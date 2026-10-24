from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import logging
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.exam import Exam, ExamSettings, ExamAssignment
from app.models.question import Question, CodingQuestion, CodingTestCase, ExamQuestion
from app.models.attempt import ExamAttempt, CodingSubmission, ExecutionResult
from app.models.user import User
from app.schemas.coding import (
    CodingSubmissionCreate,
    CodingSubmissionResponse,
    TestCaseResultResponse,
    CodingSubmissionSummaryResponse,
    CodingSubmissionListResponse,
)
from app.services.execution_provider import ExecutionProvider, ExecutionResultData, get_execution_provider
from app.services.providers.mock_execution_provider import MockExecutionProvider
from app.services.code_wrapper import prepare_code_for_execution

logger = logging.getLogger(__name__)


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _is_admin(user: User) -> bool:
    user_roles = {r.name.lower() for r in user.roles}
    if user.role:
        user_roles.add(user.role.lower())
    return "admin" in user_roles


def _is_examiner(user: User) -> bool:
    user_roles = {r.name.lower() for r in user.roles}
    if user.role:
        user_roles.add(user.role.lower())
    return "examiner" in user_roles


def validate_attempt_owner(attempt: ExamAttempt, current_user: User) -> None:
    if _is_admin(current_user) or _is_examiner(current_user):
        return
    if attempt.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you do not own this exam attempt",
        )


def validate_coding_attempt(db: Session, attempt_id: int, current_user: User) -> ExamAttempt:
    attempt = db.query(ExamAttempt).filter(ExamAttempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam attempt with ID {attempt_id} not found",
        )

    validate_attempt_owner(attempt, current_user)

    if attempt.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit code: exam attempt is already in '{attempt.status}' state",
        )

    return attempt


def validate_coding_question(
    db: Session,
    exam_id: int,
    question_id: int,
    language: str,
) -> tuple[Question, CodingQuestion, ExamQuestion]:
    exam_q = db.query(ExamQuestion).filter(
        ExamQuestion.exam_id == exam_id,
        ExamQuestion.question_id == question_id,
    ).first()

    if not exam_q:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Question with ID {question_id} is not mapped to this exam",
        )

    question = db.query(Question).filter(Question.id == question_id).first()
    if not question or question.question_type != "coding":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Question with ID {question_id} is not a coding question",
        )

    coding_question = db.query(CodingQuestion).filter(CodingQuestion.question_id == question_id).first()
    if not coding_question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Coding configuration missing for question {question_id}",
        )

    # Validate language
    allowed_langs = [l.lower() for l in (coding_question.allowed_languages or [])]
    if language.lower() not in allowed_langs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Language '{language}' is not permitted for this question. Allowed languages: {coding_question.allowed_languages}",
        )

    return question, coding_question, exam_q


def normalize_output(text: Optional[str]) -> str:
    """Normalize line endings and strip harmless whitespace."""
    if text is None:
        return ""
    norm = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in norm.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def evaluate_test_case(actual_output: Optional[str], expected_output: str) -> bool:
    """
    Deterministic test case evaluation.
    Normalizes newlines, trailing whitespace, and handles harmless whitespace formatting.
    """
    if actual_output is None or expected_output is None:
        return False

    act_norm = normalize_output(actual_output)
    exp_norm = normalize_output(expected_output)

    # 1. Exact normalized match
    if act_norm == exp_norm:
        return True

    # 2. Token-by-token comparison (handles whitespace differences like multiple spaces vs single space)
    act_tokens = act_norm.split()
    exp_tokens = exp_norm.split()
    if act_tokens == exp_tokens:
        return True

    # 3. For list/array formatted output (e.g. "[0, 1]" vs "[0,1]"), compare condensed
    act_condensed = "".join(act_norm.split())
    exp_condensed = "".join(exp_norm.split())
    if act_condensed == exp_condensed and any(c in exp_norm for c in "[]{},"):
        return True

    return False


async def execute_submission(
    db: Session,
    attempt_id: int,
    question_id: int,
    submission_in: CodingSubmissionCreate,
    current_user: User,
    provider: Optional[ExecutionProvider] = None,
) -> Dict[str, Any]:
    """
    Execute a student's code submission against all question test cases.
    - Validates attempt, question, and language.
    - Uses execution provider abstraction (Mock or Judge0).
    - Enforces timeout, memory limit, runtime error, and compilation error status priorities.
    - Stores submission record and per-testcase execution results.
    - Returns safe student-facing response (hides hidden test case inputs & expected outputs).
    """
    attempt = validate_coding_attempt(db, attempt_id, current_user)
    question, coding_question, exam_q = validate_coding_question(
        db=db,
        exam_id=attempt.exam_id,
        question_id=question_id,
        language=submission_in.language,
    )

    if not submission_in.source_code.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Source code cannot be empty",
        )

    if provider is None:
        provider = get_execution_provider()

    # Load test cases
    test_cases = db.query(CodingTestCase).filter(
        CodingTestCase.coding_question_id == coding_question.id
    ).order_by(CodingTestCase.id.asc()).all()

    # Initialize submission record
    submission = CodingSubmission(
        attempt_id=attempt.id,
        coding_question_id=coding_question.id,
        language=submission_in.language,
        source_code=submission_in.source_code,
        status="running",
        score=0.0,
        submitted_at=utc_now(),
    )
    db.add(submission)
    db.flush()

    total_tests = len(test_cases)
    passed_tests = 0
    total_time_ms = 0
    max_memory_kb = 0

    has_compilation_error = False
    has_time_limit_exceeded = False
    has_memory_limit_exceeded = False
    has_runtime_error = False
    first_compile_error = None
    first_runtime_error = None

    test_case_results_response = []

    for tc in test_cases:
        # Prepare code for execution - wrap function-based code if needed
        prepared_code, was_wrapped = prepare_code_for_execution(
            submission_in.source_code, 
            tc.input or ""
        )
        
        logger.info(
            f"Executing test case {tc.id} for question {question_id}: "
            f"input='{tc.input or ''}', wrapped={was_wrapped}"
        )
        
        exec_res: ExecutionResultData = await provider.execute(
            source_code=prepared_code,
            language=submission_in.language,
            stdin=tc.input or "",
            time_limit_ms=coding_question.time_limit_ms or 2000,
            memory_limit_kb=coding_question.memory_limit_kb or 128000,
        )
        
        logger.info(
            f"Test case {tc.id} execution result: status={exec_res.status}, "
            f"stdout='{exec_res.stdout[:100] if exec_res.stdout else 'None'}', "
            f"stderr='{exec_res.stderr[:100] if exec_res.stderr else 'None'}'"
        )

        time_ms = exec_res.execution_time_ms or 0
        mem_kb = exec_res.memory_used_kb or 0
        total_time_ms += time_ms
        if mem_kb > max_memory_kb:
            max_memory_kb = mem_kb

        # Determine verdict
        if exec_res.status == "compilation_error":
            verdict = "compile_error"
            tc_status = "compilation_error"
            has_compilation_error = True
            if not first_compile_error:
                first_compile_error = exec_res.compile_output or exec_res.error_message or "Compilation Error"
        elif exec_res.status == "time_limit_exceeded":
            verdict = "tle"
            tc_status = "time_limit_exceeded"
            has_time_limit_exceeded = True
        elif exec_res.status == "memory_limit_exceeded":
            verdict = "failed"
            tc_status = "memory_limit_exceeded"
            has_memory_limit_exceeded = True
        elif exec_res.status == "runtime_error":
            verdict = "runtime_error"
            tc_status = "runtime_error"
            has_runtime_error = True
            if not first_runtime_error:
                first_runtime_error = exec_res.error_message or exec_res.stderr or "Runtime Error"
        else:
            is_passed = evaluate_test_case(exec_res.stdout, tc.expected_output or "")
            if is_passed:
                verdict = "passed"
                tc_status = "passed"
                passed_tests += 1
            else:
                verdict = "failed"
                tc_status = "wrong_answer"

        # Record ExecutionResult in DB
        db_exec_result = ExecutionResult(
            submission_id=submission.id,
            test_case_id=tc.id,
            verdict=verdict,
            actual_output=exec_res.stdout if tc.is_sample else None,
            execution_time_ms=time_ms,
            memory_used_kb=mem_kb,
            error_message=exec_res.error_message or exec_res.compile_output or exec_res.stderr,
        )
        db.add(db_exec_result)

        # Build Safe Client Response: NEVER expose input / expected_output / actual_output for hidden test cases
        safe_item = {
            "test_case_id": tc.id,
            "is_sample": tc.is_sample,
            "status": tc_status,
            "execution_time_ms": time_ms,
            "memory_used_kb": mem_kb,
            "input": tc.input if tc.is_sample else None,
            "expected_output": tc.expected_output if tc.is_sample else None,
            "actual_output": exec_res.stdout if tc.is_sample else None,
            "error_message": (exec_res.error_message or exec_res.compile_output) if tc.is_sample else None,
        }
        test_case_results_response.append(safe_item)

        # If code failed to compile, subsequent test cases will also fail to compile
        if has_compilation_error:
            break

    # Determine final submission status
    if has_compilation_error:
        final_status = "compilation_error"
    elif has_time_limit_exceeded:
        final_status = "time_limit_exceeded"
    elif has_memory_limit_exceeded:
        final_status = "memory_limit_exceeded"
    elif has_runtime_error:
        final_status = "runtime_error"
    elif total_tests > 0 and passed_tests == total_tests:
        final_status = "accepted"
    else:
        final_status = "wrong_answer"

    # Calculate score
    effective_marks = float(exam_q.marks_override) if exam_q.marks_override is not None else float(question.marks)
    if total_tests > 0:
        calculated_score = round((passed_tests / total_tests) * effective_marks, 2)
    else:
        calculated_score = 0.0

    avg_time = total_time_ms // total_tests if total_tests > 0 else 0

    submission.status = final_status
    submission.score = calculated_score
    submission.execution_time_ms = avg_time
    submission.memory_used_kb = max_memory_kb

    try:
        db.commit()
        db.refresh(submission)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error saving coding submission: {str(e)}",
        )

    return {
        "id": submission.id,
        "attempt_id": attempt.id,
        "question_id": question_id,
        "language": submission.language,
        "source_code": submission.source_code,
        "status": submission.status,
        "verdict": submission.status.replace("_", " ").title(),
        "score": float(submission.score),
        "execution_time_ms": submission.execution_time_ms,
        "memory_used_kb": submission.memory_used_kb,
        "test_cases_total": total_tests,
        "test_cases_passed": passed_tests,
        "total_test_cases": total_tests,
        "passed_test_cases": passed_tests,
        "test_cases": test_case_results_response,
        "submitted_at": submission.submitted_at,
        "compile_error": first_compile_error,
        "runtime_error": first_runtime_error,
    }


def get_submission_by_id(
    db: Session,
    submission_id: int,
    current_user: User,
) -> Dict[str, Any]:
    submission = db.query(CodingSubmission).options(
        joinedload(CodingSubmission.attempt),
        joinedload(CodingSubmission.execution_results),
        joinedload(CodingSubmission.coding_question),
    ).filter(CodingSubmission.id == submission_id).first()

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coding submission with ID {submission_id} not found",
        )

    validate_attempt_owner(submission.attempt, current_user)

    # Fetch test cases for safe mapping
    test_cases = db.query(CodingTestCase).filter(
        CodingTestCase.coding_question_id == submission.coding_question_id
    ).all()
    tc_map = {tc.id: tc for tc in test_cases}

    results = []
    passed_count = 0
    for er in submission.execution_results:
        tc = tc_map.get(er.test_case_id)
        is_sample = tc.is_sample if tc else False
        is_passed = er.verdict == "passed"
        if is_passed:
            passed_count += 1

        results.append({
            "test_case_id": er.test_case_id,
            "is_sample": is_sample,
            "status": "passed" if is_passed else er.verdict,
            "execution_time_ms": er.execution_time_ms,
            "memory_used_kb": er.memory_used_kb,
            "input": tc.input if (tc and is_sample) else None,
            "expected_output": tc.expected_output if (tc and is_sample) else None,
            "actual_output": er.actual_output if is_sample else None,
            "error_message": er.error_message if is_sample else None,
        })

    return {
        "id": submission.id,
        "attempt_id": submission.attempt_id,
        "question_id": submission.coding_question.question_id if submission.coding_question else None,
        "language": submission.language,
        "source_code": submission.source_code,
        "status": submission.status,
        "score": float(submission.score),
        "execution_time_ms": submission.execution_time_ms,
        "memory_used_kb": submission.memory_used_kb,
        "test_cases_total": len(submission.execution_results),
        "test_cases_passed": passed_count,
        "test_cases": results,
        "submitted_at": submission.submitted_at,
    }


def list_attempt_submissions(
    db: Session,
    attempt_id: int,
    current_user: User,
) -> Dict[str, Any]:
    attempt = db.query(ExamAttempt).filter(ExamAttempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam attempt with ID {attempt_id} not found",
        )

    validate_attempt_owner(attempt, current_user)

    submissions = db.query(CodingSubmission).options(
        joinedload(CodingSubmission.coding_question)
    ).filter(
        CodingSubmission.attempt_id == attempt_id
    ).order_by(CodingSubmission.submitted_at.desc()).all()

    items = [
        {
            "id": s.id,
            "attempt_id": s.attempt_id,
            "question_id": s.coding_question.question_id if s.coding_question else None,
            "language": s.language,
            "status": s.status,
            "score": float(s.score),
            "execution_time_ms": s.execution_time_ms,
            "memory_used_kb": s.memory_used_kb,
            "submitted_at": s.submitted_at,
        }
        for s in submissions
    ]

    return {
        "attempt_id": attempt_id,
        "total_submissions": len(items),
        "submissions": items,
    }

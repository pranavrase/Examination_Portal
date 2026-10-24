from typing import Optional, List, Dict, Any
import logging
from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.core.dependencies import get_db, get_current_active_user
from app.models.user import User
from app.models.question import Question, CodingQuestion, CodingTestCase, ExamQuestion
from app.models.attempt import ExamAttempt, CodingSubmission
from app.schemas.coding import (
    CodingSubmissionCreate,
    CodingSubmissionResponse,
    CodingSubmissionListResponse,
)
from app.services import coding_service
from app.services.execution_provider import get_execution_provider
from app.services.coding_service import evaluate_test_case
from app.services.code_wrapper import prepare_code_for_execution

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/coding",
    tags=["Coding Execution Engine"],
)


class RunCodeRequest(BaseModel):
    question_id: int
    code: str
    language: str = "python"
    sample_test_cases: Optional[List[Dict[str, Any]]] = None


class DirectSubmitRequest(BaseModel):
    question_id: int
    code: str
    language: str = "python"
    attempt_id: Optional[int] = None


@router.get(
    "/questions/{exam_id}",
    status_code=status.HTTP_200_OK,
    summary="Get coding questions for an exam",
)
def get_coding_questions_by_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    user_roles = {r.name.lower() for r in current_user.roles}
    if current_user.role:
        user_roles.add(current_user.role.lower())
    is_privileged = bool(user_roles & {"admin", "examiner"})

    attempt = db.query(ExamAttempt).filter(
        ExamAttempt.exam_id == exam_id,
        ExamAttempt.student_id == current_user.id,
    ).order_by(ExamAttempt.id.desc()).first()

    if not is_privileged and attempt and attempt.status in ("submitted", "auto_submitted"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Exam attempt has already been submitted and cannot be retaken",
                "attempt_id": attempt.id,
                "status": attempt.status,
            },
        )

    exam_questions = (
        db.query(ExamQuestion)
        .join(Question, ExamQuestion.question_id == Question.id)
        .filter(ExamQuestion.exam_id == exam_id, Question.question_type == "coding")
        .order_by(ExamQuestion.question_order.asc())
        .all()
    )

    questions_out = []
    for eq in exam_questions:
        q = db.query(Question).filter(Question.id == eq.question_id).first()
        if not q:
            continue
        cd = db.query(CodingQuestion).filter(CodingQuestion.question_id == q.id).first()
        sample_cases = []
        if cd:
            sample_tcs = (
                db.query(CodingTestCase)
                .filter(CodingTestCase.coding_question_id == cd.id, CodingTestCase.is_sample == True)
                .all()
            )
            for tc in sample_tcs:
                sample_cases.append({
                    "id": tc.id,
                    "input": tc.input,
                    "expected_output": tc.expected_output,
                    "explanation": "",
                })

        allowed_langs = cd.allowed_languages if cd and cd.allowed_languages else ["python", "cpp", "java", "javascript"]
        time_limit = (cd.time_limit_ms / 1000.0) if cd and cd.time_limit_ms else 2.0
        memory_limit = int((cd.memory_limit_kb / 1024.0)) if cd and cd.memory_limit_kb else 256
        effective_marks = float(eq.marks_override) if eq.marks_override is not None else float(q.marks)

        sub = None
        if attempt and cd:
            sub = (
                db.query(CodingSubmission)
                .filter(
                    CodingSubmission.attempt_id == attempt.id,
                    CodingSubmission.coding_question_id == cd.id,
                )
                .order_by(CodingSubmission.id.desc())
                .first()
            )

        is_sub = (sub.is_final or sub.status in ("passed", "accepted", "submitted", "wrong_answer", "compilation_error")) if sub else False

        questions_out.append({
            "id": q.id,
            "question_id": q.id,
            "question_type": "coding",
            "order": eq.question_order,
            "title": f"Problem #{q.id}: {q.question_text[:40]}...",
            "category": "Coding",
            "topic": q.category.topic if q.category else "Algorithms",
            "difficulty": q.category.difficulty if q.category else "Medium",
            "marks": effective_marks,
            "time_limit": time_limit,
            "memory_limit": memory_limit,
            "allowed_languages": allowed_langs,
            "question_text": cd.problem_statement if cd and cd.problem_statement else q.question_text,
            "constraints": cd.constraints if cd and cd.constraints else "Standard execution bounds apply.",
            "starter_code": sub.source_code if sub and sub.source_code else "",
            "sample_test_cases": sample_cases,
            "is_submitted": is_sub,
            "last_language": sub.language if sub else (allowed_langs[0] if allowed_langs else "python"),
        })

    return questions_out


@router.post(
    "/run",
    status_code=status.HTTP_200_OK,
    summary="Run code against sample test cases",
)
async def run_code(
    payload: RunCodeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Executes student code against sample test cases retrieved from the database.
    Never trusts frontend test cases.
    """
    if not payload.code or not payload.code.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Source code cannot be empty.",
        )

    # 1. Fetch CodingQuestion from DB
    cd = db.query(CodingQuestion).filter(CodingQuestion.question_id == payload.question_id).first()
    if not cd:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coding configuration missing for question ID {payload.question_id}",
        )

    # 2. Fetch sample test cases from DB (never trust frontend payload)
    db_samples = (
        db.query(CodingTestCase)
        .filter(CodingTestCase.coding_question_id == cd.id, CodingTestCase.is_sample == True)
        .order_by(CodingTestCase.id.asc())
        .all()
    )

    if not db_samples:
        # Fallback to non-hidden test cases if none explicitly marked sample
        db_samples = (
            db.query(CodingTestCase)
            .filter(CodingTestCase.coding_question_id == cd.id, CodingTestCase.is_hidden == False)
            .order_by(CodingTestCase.id.asc())
            .all()
        )

    if not db_samples:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No public/sample test cases configured for question {payload.question_id}",
        )

    # Validate language against allowed languages
    if cd.allowed_languages:
        allowed = [l.lower() for l in cd.allowed_languages]
        if payload.language.lower() not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Language '{payload.language}' is not permitted for this question. Allowed: {cd.allowed_languages}",
            )

    provider = get_execution_provider()
    results = []
    all_passed = True
    total_time_ms = 0
    max_memory_kb = 0
    compile_err = None
    runtime_err = None

    time_limit_ms = cd.time_limit_ms or 2000
    memory_limit_kb = cd.memory_limit_kb or 128000

    for idx, tc in enumerate(db_samples):
        inp = tc.input or ""
        exp = tc.expected_output or ""

        # Prepare code for execution - wrap function-based code if needed
        prepared_code, was_wrapped = prepare_code_for_execution(payload.code, inp)
        
        logger.info(
            f"Run Code test case {tc.id} for question {payload.question_id}: "
            f"input='{inp}', wrapped={was_wrapped}"
        )

        exec_res = await provider.execute(
            source_code=prepared_code,
            language=payload.language,
            stdin=inp,
            time_limit_ms=time_limit_ms,
            memory_limit_kb=memory_limit_kb,
        )
        
        logger.info(
            f"Run Code test case {tc.id} result: status={exec_res.status}, "
            f"stdout='{exec_res.stdout[:100] if exec_res.stdout else 'None'}'"
        )

        exec_time = exec_res.execution_time_ms or 0
        total_time_ms += exec_time
        if (exec_res.memory_used_kb or 0) > max_memory_kb:
            max_memory_kb = exec_res.memory_used_kb

        if exec_res.status == "compilation_error":
            all_passed = False
            compile_err = exec_res.compile_output or exec_res.error_message or "Compilation Error"
            results.append({
                "id": tc.id,
                "input": inp,
                "expected_output": exp,
                "actual_output": compile_err,
                "passed": False,
                "execution_time": f"{exec_time}ms",
                "status": "compilation_error",
                "error": compile_err,
            })
            break

        if exec_res.status in ("runtime_error", "time_limit_exceeded", "memory_limit_exceeded"):
            all_passed = False
            err_msg = exec_res.error_message or exec_res.stderr or exec_res.status.replace("_", " ").title()
            if not runtime_err:
                runtime_err = err_msg
            results.append({
                "id": tc.id,
                "input": inp,
                "expected_output": exp,
                "actual_output": exec_res.stderr or err_msg,
                "passed": False,
                "execution_time": f"{exec_time}ms",
                "status": exec_res.status,
                "error": err_msg,
            })
            break

        passed = evaluate_test_case(exec_res.stdout, exp)
        if not passed:
            all_passed = False

        results.append({
            "id": tc.id,
            "input": inp,
            "expected_output": exp,
            "actual_output": (exec_res.stdout or "").strip(),
            "passed": passed,
            "execution_time": f"{exec_time}ms",
            "status": "passed" if passed else "wrong_answer",
        })

    if compile_err:
        verdict = "Compilation Error"
        overall_status = "compilation_error"
    elif runtime_err:
        verdict = "Runtime Error"
        overall_status = "runtime_error"
    elif any(r.get("status") == "time_limit_exceeded" for r in results):
        verdict = "Time Limit Exceeded"
        overall_status = "time_limit_exceeded"
    elif all_passed and results:
        verdict = "Passed"
        overall_status = "success"
    else:
        verdict = "Wrong Answer"
        overall_status = "failed"

    mem_mb = round(max_memory_kb / 1024.0, 1) if max_memory_kb > 0 else 0.0

    return {
        "verdict": verdict,
        "status": overall_status,
        "execution_time": f"{total_time_ms}ms",
        "execution_time_ms": total_time_ms,
        "memory_used": f"{mem_mb} MB" if mem_mb > 0 else "N/A",
        "memory_used_kb": max_memory_kb,
        "test_cases": results,
        "compile_error": compile_err,
        "runtime_error": runtime_err,
    }


@router.post(
    "/submit",
    status_code=status.HTTP_200_OK,
    summary="Direct coding submission endpoint for frontend context",
)
async def submit_code(
    payload: DirectSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Submits student code for final evaluation against all database test cases.
    Evaluates against existing test cases and stores marks/results in database.
    """
    logger.info(f"Coding submission request: question_id={payload.question_id}, attempt_id={payload.attempt_id}, language={payload.language}")
    
    attempt = None
    if payload.attempt_id:
        attempt = db.query(ExamAttempt).filter(ExamAttempt.id == payload.attempt_id).first()
        logger.info(f"Found attempt by ID: {attempt.id if attempt else None}")

    if not attempt:
        attempt = (
            db.query(ExamAttempt)
            .filter(ExamAttempt.student_id == current_user.id, ExamAttempt.status == "in_progress")
            .order_by(ExamAttempt.id.desc())
            .first()
        )
        logger.info(f"Found attempt by student_id and status: {attempt.id if attempt else None}")

    if not attempt:
        logger.error(f"No active in-progress exam attempt found for user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active in-progress exam attempt found. Please ensure you have an active attempt before submitting.",
        )
    
    logger.info(f"Using attempt {attempt.id} for coding submission")

    sub_create = CodingSubmissionCreate(
        language=payload.language,
        source_code=payload.code,
    )
    return await coding_service.execute_submission(
        db=db,
        attempt_id=attempt.id,
        question_id=payload.question_id,
        submission_in=sub_create,
        current_user=current_user,
    )


@router.post(
    "/attempts/{attempt_id}/questions/{question_id}/submit",
    response_model=CodingSubmissionResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit code for a coding question",
)
async def submit_coding_solution(
    attempt_id: int,
    question_id: int,
    submission_in: CodingSubmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Submit and execute code for a coding question against all test cases.
    """
    return await coding_service.execute_submission(
        db=db,
        attempt_id=attempt_id,
        question_id=question_id,
        submission_in=submission_in,
        current_user=current_user,
    )


@router.get(
    "/submissions/{submission_id}",
    response_model=CodingSubmissionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single submission result by ID",
)
def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve full details for a single coding submission.
    """
    return coding_service.get_submission_by_id(
        db=db,
        submission_id=submission_id,
        current_user=current_user,
    )


@router.get(
    "/attempts/{attempt_id}/submissions",
    response_model=CodingSubmissionListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get submission history for an exam attempt",
)
def get_attempt_submissions(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve all coding submissions made within an exam attempt.
    """
    return coding_service.list_attempt_submissions(
        db=db,
        attempt_id=attempt_id,
        current_user=current_user,
    )


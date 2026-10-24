import csv
import io
import json
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.question import (
    QuestionCategory,
    Question,
    McqOption,
    CodingQuestion,
    CodingTestCase,
    ExamQuestion,
)
from app.models.user import User
from app.schemas.question import (
    QuestionCategoryCreate,
    QuestionCategoryUpdate,
    MCQOptionCreate,
    MCQQuestionCreate,
    CodingQuestionFullCreate,
    QuestionCreate,
    QuestionUpdate,
    CodingTestCaseCreate,
    CodingTestCaseUpdate,
    SUPPORTED_LANGUAGES,
)


def _is_admin(user: User) -> bool:
    """Helper to check if user has admin privileges."""
    user_roles = {r.name.lower() for r in user.roles}
    if user.role:
        user_roles.add(user.role.lower())
    return "admin" in user_roles


def validate_question_owner(question: Question, current_user: User) -> None:
    """
    Ensure the user is either an admin or the creator of the question.
    Raises HTTP 403 Forbidden if not authorized.
    """
    if _is_admin(current_user):
        return
    if question.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you do not have permission to modify or delete another examiner's question",
        )


# ---------------------------------------------------------------------------
# Question Category Service
# ---------------------------------------------------------------------------

def create_category(db: Session, cat_in: QuestionCategoryCreate) -> QuestionCategory:
    """Create a new question category."""
    category = QuestionCategory(
        name=cat_in.name.strip().lower(),
        topic=cat_in.topic.strip() if cat_in.topic else None,
        difficulty=cat_in.difficulty.strip().lower() if cat_in.difficulty else None,
    )
    try:
        db.add(category)
        db.commit()
        db.refresh(category)
        return category
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error creating category: {str(e)}",
        )


def get_category_by_id(db: Session, category_id: int) -> QuestionCategory:
    """Retrieve category by ID."""
    category = db.query(QuestionCategory).filter(QuestionCategory.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question category with ID {category_id} not found",
        )
    return category


def list_categories(
    db: Session,
    name: Optional[str] = None,
    topic: Optional[str] = None,
    difficulty: Optional[str] = None,
) -> List[QuestionCategory]:
    """List all categories with optional filtering."""
    query = db.query(QuestionCategory)
    if name:
        query = query.filter(QuestionCategory.name.ilike(f"%{name}%"))
    if topic:
        query = query.filter(QuestionCategory.topic.ilike(f"%{topic}%"))
    if difficulty:
        query = query.filter(QuestionCategory.difficulty == difficulty.lower())
    return query.order_by(QuestionCategory.name.asc(), QuestionCategory.topic.asc()).all()


def update_category(db: Session, category_id: int, cat_in: QuestionCategoryUpdate) -> QuestionCategory:
    """Update category properties."""
    category = get_category_by_id(db=db, category_id=category_id)
    try:
        if cat_in.name is not None:
            category.name = cat_in.name.strip().lower()
        if cat_in.topic is not None:
            category.topic = cat_in.topic.strip()
        if cat_in.difficulty is not None:
            category.difficulty = cat_in.difficulty.strip().lower()

        db.commit()
        db.refresh(category)
        return category
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error updating category: {str(e)}",
        )


def delete_category(db: Session, category_id: int) -> bool:
    """Delete a category if no questions reference it."""
    category = get_category_by_id(db=db, category_id=category_id)
    question_count = db.query(Question).filter(Question.category_id == category_id).count()
    if question_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete category: {question_count} question(s) are currently referencing this category",
        )
    try:
        db.delete(category)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error deleting category: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Question Service
# ---------------------------------------------------------------------------

def create_mcq_question(db: Session, mcq_in: MCQQuestionCreate, creator_id: int) -> Question:
    """
    Create an MCQ question along with its options atomically.
    """
    # Verify category exists
    get_category_by_id(db=db, category_id=mcq_in.category_id)

    try:
        question = Question(
            category_id=mcq_in.category_id,
            question_type="mcq",
            question_text=mcq_in.question_text.strip(),
            marks=mcq_in.marks,
            created_by=creator_id,
        )
        db.add(question)
        db.flush()

        for opt in mcq_in.options:
            mcq_opt = McqOption(
                question_id=question.id,
                option_text=opt.option_text.strip(),
                is_correct=opt.is_correct,
            )
            db.add(mcq_opt)

        db.commit()
        db.refresh(question)
        return question
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Integrity error creating MCQ question: {str(e.orig)}",
        )
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error creating MCQ question: {str(e)}",
        )


def create_coding_question(db: Session, coding_in: CodingQuestionFullCreate, creator_id: int) -> Question:
    """
    Create a Coding question along with its coding details and optional test cases atomically.
    """
    # Verify category exists
    get_category_by_id(db=db, category_id=coding_in.category_id)

    try:
        question = Question(
            category_id=coding_in.category_id,
            question_type="coding",
            question_text=coding_in.question_text.strip(),
            marks=coding_in.marks,
            created_by=creator_id,
        )
        db.add(question)
        db.flush()

        coding_details = CodingQuestion(
            question_id=question.id,
            problem_statement=coding_in.problem_statement.strip(),
            constraints=coding_in.constraints.strip() if coding_in.constraints else None,
            allowed_languages=[l.lower() for l in coding_in.allowed_languages],
            time_limit_ms=coding_in.time_limit_ms,
            memory_limit_kb=coding_in.memory_limit_kb,
        )
        db.add(coding_details)
        db.flush()

        if coding_in.test_cases:
            for tc in coding_in.test_cases:
                test_case = CodingTestCase(
                    coding_question_id=coding_details.id,
                    input=tc.input if tc.input is not None else "",
                    expected_output=tc.expected_output.strip(),
                    is_sample=tc.is_sample,
                    is_hidden=tc.is_hidden,
                )
                db.add(test_case)

        db.commit()
        db.refresh(question)
        return question
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Integrity error creating coding question: {str(e.orig)}",
        )
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error creating coding question: {str(e)}",
        )


def create_question(db: Session, q_in: QuestionCreate, creator_id: int) -> Question:
    """
    Unified entrypoint to create either MCQ or Coding question.
    """
    cat_id = q_in.category_id
    if not cat_id and q_in.category:
        cat_name = q_in.category.strip().lower()
        topic_name = q_in.topic.strip() if q_in.topic else None
        diff_name = q_in.difficulty.strip().lower() if q_in.difficulty else "medium"
        cat = db.query(QuestionCategory).filter(
            QuestionCategory.name == cat_name,
            QuestionCategory.topic == topic_name,
            QuestionCategory.difficulty == diff_name,
        ).first()
        if not cat:
            cat = QuestionCategory(
                name=cat_name,
                topic=topic_name,
                difficulty=diff_name if diff_name in {"easy", "medium", "hard"} else "medium",
            )
            db.add(cat)
            db.flush()
        cat_id = cat.id

    if q_in.question_type == "mcq":
        mcq_payload = MCQQuestionCreate(
            category_id=cat_id,
            question_type="mcq",
            question_text=q_in.question_text,
            marks=q_in.marks,
            options=q_in.options or [],
        )
        return create_mcq_question(db=db, mcq_in=mcq_payload, creator_id=creator_id)
    else:
        coding_payload = CodingQuestionFullCreate(
            category_id=cat_id,
            question_type="coding",
            question_text=q_in.question_text,
            marks=q_in.marks,
            problem_statement=q_in.problem_statement or q_in.question_text,
            constraints=q_in.constraints,
            allowed_languages=q_in.allowed_languages or ["python", "java", "cpp", "c"],
            time_limit_ms=q_in.time_limit_ms or 2000,
            memory_limit_kb=q_in.memory_limit_kb or 256000,
            test_cases=q_in.test_cases,
        )
        return create_coding_question(db=db, coding_in=coding_payload, creator_id=creator_id)


def add_test_cases(
    db: Session,
    question_id: int,
    test_cases_in: List[CodingTestCaseCreate],
    current_user: User,
) -> List[CodingTestCase]:
    """
    Add test cases to a coding question.
    """
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question with ID {question_id} not found",
        )

    validate_question_owner(question, current_user)

    if question.question_type != "coding" or not question.coding_details:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Question {question_id} is not a coding question",
        )

    coding_question_id = question.coding_details.id
    new_cases = []
    try:
        for tc in test_cases_in:
            test_case = CodingTestCase(
                coding_question_id=coding_question_id,
                input=tc.input if tc.input is not None else "",
                expected_output=tc.expected_output.strip(),
                is_sample=tc.is_sample,
                is_hidden=tc.is_hidden,
            )
            db.add(test_case)
            new_cases.append(test_case)

        db.commit()
        for tc in new_cases:
            db.refresh(tc)
        return new_cases
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Integrity error adding test cases: {str(e.orig)}",
        )
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error adding test cases: {str(e)}",
        )


def update_test_case(
    db: Session,
    question_id: int,
    test_case_id: int,
    tc_in: CodingTestCaseUpdate,
    current_user: User,
) -> CodingTestCase:
    """Update a specific coding test case."""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question with ID {question_id} not found",
        )
    validate_question_owner(question, current_user)

    test_case = db.query(CodingTestCase).filter(CodingTestCase.id == test_case_id).first()
    if not test_case or (question.coding_details and test_case.coding_question_id != question.coding_details.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test case with ID {test_case_id} not found on question {question_id}",
        )

    try:
        if tc_in.input is not None:
            test_case.input = tc_in.input
        if tc_in.expected_output is not None:
            test_case.expected_output = tc_in.expected_output.strip()
        if tc_in.is_sample is not None:
            test_case.is_sample = tc_in.is_sample
        if tc_in.is_hidden is not None:
            test_case.is_hidden = tc_in.is_hidden

        db.commit()
        db.refresh(test_case)
        return test_case
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error updating test case: {str(e)}",
        )


def delete_test_case(
    db: Session,
    question_id: int,
    test_case_id: int,
    current_user: User,
) -> bool:
    """Delete a specific test case."""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question with ID {question_id} not found",
        )
    validate_question_owner(question, current_user)

    test_case = db.query(CodingTestCase).filter(CodingTestCase.id == test_case_id).first()
    if not test_case or (question.coding_details and test_case.coding_question_id != question.coding_details.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test case with ID {test_case_id} not found on question {question_id}",
        )

    try:
        db.delete(test_case)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error deleting test case: {str(e)}",
        )


def get_question_by_id(db: Session, question_id: int, current_user: User) -> Question:
    """
    Retrieve question by ID with all related objects.
    Admins can view any question; Examiners can view all question bank items for reuse or their own.
    """
    question = db.query(Question).options(
        joinedload(Question.category),
        joinedload(Question.mcq_options),
        joinedload(Question.coding_details).joinedload(CodingQuestion.test_cases),
    ).filter(Question.id == question_id).first()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question with ID {question_id} not found",
        )

    return question


def update_question(
    db: Session,
    question_id: int,
    q_in: QuestionUpdate,
    current_user: User,
) -> Question:
    """
    Update a question's base fields, options (if MCQ), or coding details (if Coding).
    Rejects invalid cross-type conversions.
    """
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question with ID {question_id} not found",
        )

    validate_question_owner(question, current_user)

    # Validate category if provided
    if q_in.category_id is not None:
        get_category_by_id(db=db, category_id=q_in.category_id)
        question.category_id = q_in.category_id
    elif q_in.category is not None:
        cat_name = q_in.category.strip().lower()
        topic_name = q_in.topic.strip() if q_in.topic else None
        diff_name = q_in.difficulty.strip().lower() if q_in.difficulty else "medium"
        cat = db.query(QuestionCategory).filter(
            QuestionCategory.name == cat_name,
            QuestionCategory.topic == topic_name,
            QuestionCategory.difficulty == diff_name,
        ).first()
        if not cat:
            cat = QuestionCategory(
                name=cat_name,
                topic=topic_name,
                difficulty=diff_name if diff_name in {"easy", "medium", "hard"} else "medium",
            )
            db.add(cat)
            db.flush()
        question.category_id = cat.id

    try:
        if q_in.question_text is not None:
            question.question_text = q_in.question_text.strip()
        if q_in.marks is not None:
            question.marks = q_in.marks

        if question.question_type == "mcq":
            if q_in.problem_statement or q_in.constraints or q_in.allowed_languages or q_in.time_limit_ms or q_in.memory_limit_kb:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot apply coding fields to an MCQ question",
                )
            if q_in.options is not None:
                # Replace existing options
                db.query(McqOption).filter(McqOption.question_id == question.id).delete()
                for opt in q_in.options:
                    new_opt = McqOption(
                        question_id=question.id,
                        option_text=opt.option_text.strip(),
                        is_correct=opt.is_correct,
                    )
                    db.add(new_opt)

        elif question.question_type == "coding":
            if q_in.options is not None and len(q_in.options) > 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot attach MCQ options to a coding question",
                )
            if question.coding_details:
                if q_in.problem_statement is not None:
                    question.coding_details.problem_statement = q_in.problem_statement.strip()
                if q_in.constraints is not None:
                    question.coding_details.constraints = q_in.constraints.strip()
                if q_in.allowed_languages is not None:
                    question.coding_details.allowed_languages = [l.lower() for l in q_in.allowed_languages]
                if q_in.time_limit_ms is not None:
                    question.coding_details.time_limit_ms = q_in.time_limit_ms
                if q_in.memory_limit_kb is not None:
                    question.coding_details.memory_limit_kb = q_in.memory_limit_kb

        db.commit()
        db.refresh(question)
        return question
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Integrity error updating question: {str(e.orig)}",
        )
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error updating question: {str(e)}",
        )


def delete_question(db: Session, question_id: int, current_user: User) -> bool:
    """
    Delete a question and its cascading child records.
    Prevents deletion if question is mapped to active exams.
    """
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question with ID {question_id} not found",
        )

    validate_question_owner(question, current_user)

    # Check for exam associations
    exam_mapping_count = db.query(ExamQuestion).filter(ExamQuestion.question_id == question_id).count()
    if exam_mapping_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete question: it is currently mapped to {exam_mapping_count} exam(s)",
        )

    try:
        db.delete(question)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error deleting question: {str(e)}",
        )


def list_questions_by_filter(
    db: Session,
    current_user: User,
    category: Optional[str] = None,
    topic: Optional[str] = None,
    difficulty: Optional[str] = None,
    question_type: Optional[str] = None,
    created_by: Optional[int] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    """
    List questions with multi-criteria filtering and pagination.
    """
    query = db.query(Question).options(
        joinedload(Question.category),
        joinedload(Question.mcq_options),
        joinedload(Question.coding_details).joinedload(CodingQuestion.test_cases),
    )

    if category or topic or difficulty:
        query = query.join(QuestionCategory, Question.category_id == QuestionCategory.id)
        if category:
            query = query.filter(QuestionCategory.name.ilike(f"%{category}%"))
        if topic:
            query = query.filter(QuestionCategory.topic.ilike(f"%{topic}%"))
        if difficulty:
            query = query.filter(QuestionCategory.difficulty == difficulty.lower())

    if question_type:
        query = query.filter(Question.question_type == question_type.lower())

    if created_by:
        query = query.filter(Question.created_by == created_by)

    if search:
        query = query.filter(Question.question_text.ilike(f"%{search}%"))

    total = query.count()
    offset = (page - 1) * page_size
    questions = query.order_by(Question.created_at.desc()).offset(offset).limit(page_size).all()

    return {
        "items": questions,
        "page": page,
        "page_size": page_size,
        "total": total,
    }


# ---------------------------------------------------------------------------
# Bulk Import Service
# ---------------------------------------------------------------------------

def bulk_import_questions(
    db: Session,
    file_content: bytes,
    filename: str,
    creator_id: int,
) -> Dict[str, Any]:
    """
    Parse and import questions from a CSV file.
    Supports both MCQ and Coding question rows with robust row-level error reporting.
    """
    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only .csv files are supported for bulk import",
        )

    try:
        decoded = file_content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            decoded = file_content.decode("latin-1")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to decode CSV file. Please ensure valid UTF-8 encoding",
            )

    reader = csv.DictReader(io.StringIO(decoded))
    if not reader.fieldnames:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded CSV file is empty or missing headers",
        )

    # Normalize headers
    normalized_fieldnames = {f.strip().lower(): f for f in reader.fieldnames if f}
    required_base = {"question_type", "category", "question_text", "marks"}
    missing = required_base - set(normalized_fieldnames.keys())
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV missing required columns: {', '.join(missing)}",
        )

    imported_questions = []
    row_errors = []
    row_idx = 1

    for row in reader:
        row_idx += 1
        clean_row = {k.strip().lower(): v.strip() for k, v in row.items() if k and v is not None}
        q_type = clean_row.get("question_type", "").lower()
        cat_name = clean_row.get("category", "")
        topic = clean_row.get("topic", "")
        difficulty = clean_row.get("difficulty", "medium").lower()
        q_text = clean_row.get("question_text", "")
        marks_str = clean_row.get("marks", "1")

        if not q_text:
            row_errors.append({"row_index": row_idx, "error": "question_text cannot be empty"})
            continue

        try:
            marks = float(marks_str)
            if marks <= 0:
                row_errors.append({"row_index": row_idx, "error": "marks must be greater than zero"})
                continue
        except ValueError:
            row_errors.append({"row_index": row_idx, "error": f"Invalid marks value: '{marks_str}'"})
            continue

        if q_type not in {"mcq", "coding"}:
            row_errors.append({"row_index": row_idx, "error": f"Invalid question_type: '{q_type}'. Must be 'mcq' or 'coding'"})
            continue

        # Find or create category
        cat = db.query(QuestionCategory).filter(
            QuestionCategory.name == cat_name.lower(),
            QuestionCategory.topic == (topic if topic else None),
            QuestionCategory.difficulty == (difficulty if difficulty else None),
        ).first()

        if not cat:
            cat = QuestionCategory(
                name=cat_name.lower(),
                topic=topic if topic else None,
                difficulty=difficulty if difficulty in {"easy", "medium", "hard"} else "medium",
            )
            db.add(cat)
            db.flush()

        if q_type == "mcq":
            opt_a = clean_row.get("option_a", "")
            opt_b = clean_row.get("option_b", "")
            opt_c = clean_row.get("option_c", "")
            opt_d = clean_row.get("option_d", "")
            correct_opt = clean_row.get("correct_option", "").strip().lower()

            options = []
            if opt_a:
                options.append(MCQOptionCreate(option_text=opt_a, is_correct=(correct_opt in {"a", "1", "opt_a", "option_a", opt_a.lower()})))
            if opt_b:
                options.append(MCQOptionCreate(option_text=opt_b, is_correct=(correct_opt in {"b", "2", "opt_b", "option_b", opt_b.lower()})))
            if opt_c:
                options.append(MCQOptionCreate(option_text=opt_c, is_correct=(correct_opt in {"c", "3", "opt_c", "option_c", opt_c.lower()})))
            if opt_d:
                options.append(MCQOptionCreate(option_text=opt_d, is_correct=(correct_opt in {"d", "4", "opt_d", "option_d", opt_d.lower()})))

            if len(options) < 2:
                row_errors.append({"row_index": row_idx, "error": "MCQ requires at least 2 options (option_a, option_b)"})
                continue
            if not any(o.is_correct for o in options):
                row_errors.append({"row_index": row_idx, "error": f"No correct option matched '{correct_opt}' among provided options"})
                continue

            try:
                mcq_payload = MCQQuestionCreate(
                    category_id=cat.id,
                    question_type="mcq",
                    question_text=q_text,
                    marks=marks,
                    options=options,
                )
                q = create_mcq_question(db=db, mcq_in=mcq_payload, creator_id=creator_id)
                imported_questions.append(q)
            except Exception as e:
                row_errors.append({"row_index": row_idx, "error": str(e)})

        elif q_type == "coding":
            prob_statement = clean_row.get("problem_statement", clean_row.get("statement", q_text))
            constraints = clean_row.get("constraints", None)
            lang_str = clean_row.get("allowed_languages", "python,java,cpp,c")
            allowed_langs = [l.strip().lower() for l in lang_str.split(",") if l.strip()]

            time_limit = 2000
            if "time_limit_ms" in clean_row:
                try:
                    time_limit = int(clean_row["time_limit_ms"])
                except ValueError:
                    pass

            mem_limit = 256000
            if "memory_limit_kb" in clean_row:
                try:
                    mem_limit = int(clean_row["memory_limit_kb"])
                except ValueError:
                    pass

            try:
                coding_payload = CodingQuestionFullCreate(
                    category_id=cat.id,
                    question_type="coding",
                    question_text=q_text,
                    marks=marks,
                    problem_statement=prob_statement,
                    constraints=constraints,
                    allowed_languages=allowed_langs,
                    time_limit_ms=time_limit,
                    memory_limit_kb=mem_limit,
                )
                q = create_coding_question(db=db, coding_in=coding_payload, creator_id=creator_id)
                imported_questions.append(q)
            except Exception as e:
                row_errors.append({"row_index": row_idx, "error": str(e)})

    return {
        "message": f"Bulk import complete: {len(imported_questions)} succeeded, {len(row_errors)} failed",
        "total_rows": (row_idx - 1),
        "successful_imports": len(imported_questions),
        "failed_imports": len(row_errors),
        "errors": row_errors,
        "imported_questions": imported_questions,
    }

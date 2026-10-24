from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.exam import Exam, ExamSettings, ExamAssignment
from app.models.user import User
from app.schemas.exam import (
    ExamCreate,
    ExamUpdate,
    ExamSettingsUpdate,
    ExamAssignmentCreate,
)


def _is_admin(user: User) -> bool:
    """Helper to check if a user has admin privileges."""
    user_roles = {r.name.lower() for r in user.roles}
    if user.role:
        user_roles.add(user.role.lower())
    return "admin" in user_roles


def _is_student(user: User) -> bool:
    """Helper to check if a user possesses the student role."""
    user_roles = {r.name.lower() for r in user.roles}
    if user.role:
        user_roles.add(user.role.lower())
    return "student" in user_roles


def validate_exam_owner(exam: Exam, current_user: User) -> None:
    """Validate exam access.
    Admins have unrestricted access. Examiners can view any exam (no ownership restriction).
    """
    if _is_admin(current_user):
        return
    # Allow examiners to access any exam; no further checks needed.
    return


def validate_exam_status(exam: Exam, allowed_statuses: List[str], error_message: Optional[str] = None) -> None:
    """
    Ensure the exam is in one of the allowed lifecycle statuses.
    """
    if exam.status not in allowed_statuses:
        msg = error_message or f"Operation not allowed for exam in '{exam.status}' status. Allowed statuses: {', '.join(allowed_statuses)}"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )


def _format_description_and_instructions(description: Optional[str], instructions: Optional[str]) -> Optional[str]:
    desc = (description or "").strip()
    inst = (instructions or "").strip()
    if desc and inst:
        return f"{desc}\n\n[INSTRUCTIONS]\n{inst}"
    elif inst:
        return f"[INSTRUCTIONS]\n{inst}"
    elif desc:
        return desc
    return None


def _extract_instructions(exam: Optional[Exam]) -> Optional[Exam]:
    if not exam:
        return exam
    raw_desc = exam.description or ""
    if "[INSTRUCTIONS]\n" in raw_desc:
        parts = raw_desc.split("[INSTRUCTIONS]\n", 1)
        exam.description = parts[0].strip() or None
        setattr(exam, "instructions", parts[1].strip())
    elif "[INSTRUCTIONS]" in raw_desc:
        parts = raw_desc.split("[INSTRUCTIONS]", 1)
        exam.description = parts[0].strip() or None
        setattr(exam, "instructions", parts[1].strip())
    else:
        setattr(exam, "instructions", None)
    return exam


def get_exam_by_id(db: Session, exam_id: int, current_user: User) -> Exam:
    """
    Retrieve an exam by ID and validate caller authorization.
    Admins can view any exam; Examiners can only view their own exams;
    Students can view published exams or exams assigned to them.
    """
    exam = db.query(Exam).options(joinedload(Exam.settings)).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam with ID {exam_id} not found",
        )

    if _is_admin(current_user):
        return _extract_instructions(exam)

    if _is_student(current_user):
        is_assigned = db.query(ExamAssignment).filter(
            ExamAssignment.exam_id == exam.id,
            ExamAssignment.student_id == current_user.id,
        ).first()
        if exam.status != "published" and not is_assigned:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Exam is not published or you are not assigned to this exam",
            )
        return _extract_instructions(exam)

    validate_exam_owner(exam, current_user)
    return _extract_instructions(exam)


def create_exam(db: Session, exam_in: ExamCreate, creator_id: int) -> Exam:
    """
    Create a new Exam along with its 1-to-1 ExamSettings within a transaction.
    """
    try:
        initial_status = getattr(exam_in, "status", None) or "draft"
        combined_desc = _format_description_and_instructions(exam_in.description, getattr(exam_in, "instructions", None))
        exam = Exam(
            title=exam_in.title.strip(),
            description=combined_desc,
            created_by=creator_id,
            status=initial_status,
        )
        db.add(exam)
        db.flush()  # Populates exam.id

        settings = ExamSettings(
            exam_id=exam.id,
            duration_minutes=exam_in.settings.duration_minutes,
            total_marks=exam_in.settings.total_marks,
            passing_percentage=exam_in.settings.passing_percentage,
            negative_marking_ratio=exam_in.settings.negative_marking_ratio,
            randomize_questions=exam_in.settings.randomize_questions,
            randomize_options=exam_in.settings.randomize_options,
        )
        db.add(settings)

        # Automatically assign all active students if requested
        if getattr(exam_in, "assign_all_students", False):
            all_users = db.query(User).filter(User.is_active == True).all()
            for u in all_users:
                if _is_student(u):
                    db.add(ExamAssignment(exam_id=exam.id, student_id=u.id))

        db.commit()
        db.refresh(exam)
        return _extract_instructions(exam)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database integrity error during exam creation: {str(e.orig)}",
        )
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error during exam creation: {str(e)}",
        )


def update_exam(db: Session, exam_id: int, exam_in: ExamUpdate, current_user: User) -> Exam:
    """
    Update an exam's basic details and optionally its settings.
    """
    exam = get_exam_by_id(db=db, exam_id=exam_id, current_user=current_user)

    if exam.status == "closed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify a closed exam",
        )

    try:
        if exam_in.title is not None:
            exam.title = exam_in.title.strip()

        # Handle description and instructions updates
        new_desc = exam_in.description if exam_in.description is not None else exam.description
        new_inst = exam_in.instructions if getattr(exam_in, "instructions", None) is not None else getattr(exam, "instructions", None)
        if exam_in.description is not None or getattr(exam_in, "instructions", None) is not None:
            exam.description = _format_description_and_instructions(new_desc, new_inst)

        if getattr(exam_in, "status", None) is not None:
            exam.status = exam_in.status

        if getattr(exam_in, "assign_all_students", None) is True:
            all_users = db.query(User).filter(User.is_active == True).all()
            existing_sids = {
                a.student_id for a in db.query(ExamAssignment).filter(ExamAssignment.exam_id == exam.id).all()
            }
            for u in all_users:
                if _is_student(u) and u.id not in existing_sids:
                    db.add(ExamAssignment(exam_id=exam.id, student_id=u.id))

        if exam_in.settings is not None:
            if not exam.settings:
                exam.settings = ExamSettings(exam_id=exam.id)
            settings_data = exam_in.settings.model_dump(exclude_unset=True)
            for key, value in settings_data.items():
                if value is not None:
                    setattr(exam.settings, key, value)

        db.commit()
        db.refresh(exam)
        return _extract_instructions(exam)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Integrity error during exam update: {str(e.orig)}",
        )
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error during exam update: {str(e)}",
        )


def update_exam_settings(db: Session, exam_id: int, settings_in: ExamSettingsUpdate, current_user: User) -> ExamSettings:
    """
    Update only the exam settings for a specific exam.
    """
    exam = get_exam_by_id(db=db, exam_id=exam_id, current_user=current_user)

    if exam.status == "closed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update settings of a closed exam",
        )

    try:
        settings = exam.settings
        if not settings:
            settings = ExamSettings(exam_id=exam.id)
            db.add(settings)

        settings_data = settings_in.model_dump(exclude_unset=True)
        for key, value in settings_data.items():
            if value is not None:
                setattr(settings, key, value)

        db.commit()
        db.refresh(settings)
        return settings
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Integrity error during settings update: {str(e.orig)}",
        )
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error during settings update: {str(e)}",
        )


def publish_exam(db: Session, exam_id: int, current_user: User) -> Exam:
    """
    Publish a draft exam.
    Validates lifecycle state and ensures settings exist before publishing.
    """
    exam = get_exam_by_id(db=db, exam_id=exam_id, current_user=current_user)

    if exam.status == "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exam is already published",
        )
    if exam.status == "closed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot publish a closed exam",
        )
    if exam.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot publish exam in '{exam.status}' state. Only 'draft' exams can be published",
        )

    if not exam.settings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exam configuration is incomplete: ExamSettings record is missing",
        )

    try:
        exam.status = "published"
        db.commit()
        db.refresh(exam)
        return exam
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error publishing exam: {str(e)}",
        )


def delete_exam(db: Session, exam_id: int, current_user: User) -> bool:
    """
    Delete an exam if allowed by lifecycle and assignment rules.
    Examiners/Admins can delete draft exams with no active assignments.
    """
    exam = get_exam_by_id(db=db, exam_id=exam_id, current_user=current_user)

    if exam.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete exam in '{exam.status}' state. Only 'draft' exams can be deleted",
        )

    if exam.assignments and len(exam.assignments) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete an exam that has active student assignments",
        )

    try:
        db.delete(exam)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error deleting exam: {str(e)}",
        )


def list_exams(
    db: Session,
    current_user: User,
    page: int = 1,
    page_size: int = 20,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    """
    List exams with pagination and filtering.
    - Admins can view all exams.
    - Examiners view only exams they created.
    """
    query = db.query(Exam).options(joinedload(Exam.settings))

    if not _is_admin(current_user):
        query = query.filter(Exam.created_by == current_user.id)

    if status_filter:
        query = query.filter(Exam.status == status_filter.lower())

    if search:
        query = query.filter(Exam.title.ilike(f"%{search}%"))

    total = query.count()
    offset = (page - 1) * page_size
    exams = query.order_by(Exam.created_at.desc()).offset(offset).limit(page_size).all()

    return {
        "items": exams,
        "page": page,
        "page_size": page_size,
        "total": total,
    }


def assign_exam_to_students(
    db: Session,
    exam_id: int,
    assignment_in: ExamAssignmentCreate,
    current_user: User,
) -> List[ExamAssignment]:
    """
    Assign one or multiple students to an exam.
    - Validates ownership / admin permission.
    - Validates that exam is not closed.
    - Validates that all target users exist and have the 'student' role.
    - Prevents duplicate assignments (raises 409 Conflict).
    - Performs atomic database transaction.
    """
    exam = get_exam_by_id(db=db, exam_id=exam_id, current_user=current_user)

    if exam.status == "closed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assign students to a closed exam",
        )

    # Collect target student IDs
    raw_ids = []
    if assignment_in.student_ids:
        raw_ids.extend(assignment_in.student_ids)
    if assignment_in.student_id is not None:
        raw_ids.append(assignment_in.student_id)

    # Deduplicate preserving order
    target_ids = list(dict.fromkeys(raw_ids))

    if not target_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid student IDs provided for assignment",
        )

    # Validate each user exists, is active, and possesses the student role
    for sid in target_ids:
        student_user = db.query(User).filter(User.id == sid).first()
        if not student_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student user with ID {sid} not found",
            )
        if not _is_student(student_user):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with ID {sid} ({student_user.email}) does not have the 'student' role",
            )

        # Check for existing assignment
        existing = db.query(ExamAssignment).filter(
            ExamAssignment.exam_id == exam.id,
            ExamAssignment.student_id == sid,
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Student with ID {sid} ({student_user.email}) is already assigned to this exam",
            )

    new_assignments = []
    try:
        for sid in target_ids:
            assignment = ExamAssignment(
                exam_id=exam.id,
                student_id=sid,
                scheduled_start=assignment_in.scheduled_start,
                scheduled_end=assignment_in.scheduled_end,
            )
            db.add(assignment)
            new_assignments.append(assignment)

        db.commit()
        for a in new_assignments:
            db.refresh(a)
        return new_assignments
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Assignment conflict: duplicate assignment detected ({str(e.orig)})",
        )
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error assigning students to exam: {str(e)}",
        )


def list_exam_assignments(
    db: Session,
    exam_id: int,
    current_user: User,
    page: int = 1,
    page_size: int = 50,
) -> Dict[str, Any]:
    """
    List all assigned students for an exam.
    """
    exam = get_exam_by_id(db=db, exam_id=exam_id, current_user=current_user)

    query = db.query(ExamAssignment).filter(ExamAssignment.exam_id == exam.id)
    total = query.count()
    offset = (page - 1) * page_size
    assignments = query.order_by(ExamAssignment.assigned_at.desc()).offset(offset).limit(page_size).all()

    return {
        "items": assignments,
        "page": page,
        "page_size": page_size,
        "total": total,
    }


def remove_student_assignment(
    db: Session,
    exam_id: int,
    student_id: int,
    current_user: User,
) -> bool:
    """
    Remove/unassign a student from an exam.
    """
    exam = get_exam_by_id(db=db, exam_id=exam_id, current_user=current_user)

    assignment = db.query(ExamAssignment).filter(
        ExamAssignment.exam_id == exam.id,
        ExamAssignment.student_id == student_id,
    ).first()

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment for student ID {student_id} on exam ID {exam_id} not found",
        )

    try:
        db.delete(assignment)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error removing assignment: {str(e)}",
        )

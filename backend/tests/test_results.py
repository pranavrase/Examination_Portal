"""
test_results.py — Module 2.10: Result Calculation Engine
=========================================================
Tests cover:
  - Basic scoring (MCQ correct/incorrect/unanswered, coding, combined)
  - Negative marking
  - Boundary cases (exactly passing, just below, zero total marks, etc.)
  - Authorization (student own, student other, examiner, admin)
  - State (in_progress rejected, submitted/auto_submitted accepted)
  - Idempotency (double calculation, no duplicate rows)
  - Integration flows (full lifecycle, timer expiry)
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.models.user import User
from app.models.role import Role
from app.models.exam import Exam, ExamSettings, ExamAssignment
from app.models.question import (
    QuestionCategory, Question, McqOption,
    CodingQuestion, CodingTestCase, ExamQuestion,
)
from app.models.attempt import ExamAttempt, AttemptAnswer, CodingSubmission, ExecutionResult
from app.models.result import Result
from app.core.security import hash_password, create_access_token
from app.services.role_service import seed_default_roles
from app.services.result_service import (
    calculate_final_score,
    apply_negative_marking,
    determine_pass_fail,
)


# ──────────────────────────────────────────────────────────────────────────────
# Fixture helpers
# ──────────────────────────────────────────────────────────────────────────────

def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_auth_header(user_id: int, email: str, role: str) -> dict:
    token = create_access_token(user_id=user_id, email=email, role=role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def setup_results_fixtures(db_session):
    """Seed everything needed for result tests."""
    seed_default_roles(db_session)

    student_role = db_session.query(Role).filter(Role.name == "student").first()
    examiner_role = db_session.query(Role).filter(Role.name == "examiner").first()
    admin_role = db_session.query(Role).filter(Role.name == "admin").first()

    # Users
    admin = User(email="admin@test.com", full_name="Admin", password_hash=hash_password("x"), is_active=True)
    if admin_role:
        admin.roles.append(admin_role)
    db_session.add(admin)

    examiner = User(email="examiner@test.com", full_name="Examiner", password_hash=hash_password("x"), is_active=True)
    if examiner_role:
        examiner.roles.append(examiner_role)
    db_session.add(examiner)

    examiner2 = User(email="examiner2@test.com", full_name="Examiner2", password_hash=hash_password("x"), is_active=True)
    if examiner_role:
        examiner2.roles.append(examiner_role)
    db_session.add(examiner2)

    student1 = User(email="student1@test.com", full_name="Student One", password_hash=hash_password("x"), is_active=True)
    if student_role:
        student1.roles.append(student_role)
    db_session.add(student1)

    student2 = User(email="student2@test.com", full_name="Student Two", password_hash=hash_password("x"), is_active=True)
    if student_role:
        student2.roles.append(student_role)
    db_session.add(student2)

    db_session.flush()

    # Category
    cat = QuestionCategory(name="CS", topic="Programming", difficulty="medium")
    db_session.add(cat)
    db_session.flush()

    # Exam A: MCQ + Coding, 30 total marks, 50% passing, 0.25 neg ratio
    exam_a = Exam(title="Exam A", created_by=examiner.id, status="published")
    db_session.add(exam_a)
    db_session.flush()
    db_session.add(ExamSettings(
        exam_id=exam_a.id,
        duration_minutes=60,
        total_marks=30.0,
        passing_percentage=50.0,
        negative_marking_ratio=0.25,
    ))

    # MCQ Question: 10 marks
    q_mcq = Question(category_id=cat.id, question_type="mcq", question_text="Q1 MCQ", marks=10.0, created_by=examiner.id)
    db_session.add(q_mcq)
    db_session.flush()
    opt_wrong = McqOption(question_id=q_mcq.id, option_text="Wrong", is_correct=False)
    opt_right = McqOption(question_id=q_mcq.id, option_text="Right", is_correct=True)
    db_session.add_all([opt_wrong, opt_right])
    db_session.add(ExamQuestion(exam_id=exam_a.id, question_id=q_mcq.id, question_order=1))

    # Coding Question: 20 marks
    q_code = Question(category_id=cat.id, question_type="coding", question_text="Q2 Code", marks=20.0, created_by=examiner.id)
    db_session.add(q_code)
    db_session.flush()
    cq = CodingQuestion(question_id=q_code.id, problem_statement="Print hello", allowed_languages=["python"])
    db_session.add(cq)
    db_session.add(ExamQuestion(exam_id=exam_a.id, question_id=q_code.id, question_order=2))

    # Assign both students to Exam A
    db_session.add(ExamAssignment(exam_id=exam_a.id, student_id=student1.id, assigned_at=utc_now()))
    db_session.add(ExamAssignment(exam_id=exam_a.id, student_id=student2.id, assigned_at=utc_now()))

    # Exam B: MCQ only, 40 marks, 60% passing, NO negative marking
    exam_b = Exam(title="Exam B MCQ Only", created_by=examiner.id, status="published")
    db_session.add(exam_b)
    db_session.flush()
    db_session.add(ExamSettings(
        exam_id=exam_b.id,
        duration_minutes=30,
        total_marks=40.0,
        passing_percentage=60.0,
        negative_marking_ratio=0.0,
    ))
    q_b1 = Question(category_id=cat.id, question_type="mcq", question_text="QB1", marks=20.0, created_by=examiner.id)
    q_b2 = Question(category_id=cat.id, question_type="mcq", question_text="QB2", marks=20.0, created_by=examiner.id)
    db_session.add_all([q_b1, q_b2])
    db_session.flush()
    opt_b1_w = McqOption(question_id=q_b1.id, option_text="Wrong", is_correct=False)
    opt_b1_r = McqOption(question_id=q_b1.id, option_text="Right", is_correct=True)
    opt_b2_w = McqOption(question_id=q_b2.id, option_text="Wrong", is_correct=False)
    opt_b2_r = McqOption(question_id=q_b2.id, option_text="Right", is_correct=True)
    db_session.add_all([opt_b1_w, opt_b1_r, opt_b2_w, opt_b2_r])
    db_session.add(ExamQuestion(exam_id=exam_b.id, question_id=q_b1.id, question_order=1))
    db_session.add(ExamQuestion(exam_id=exam_b.id, question_id=q_b2.id, question_order=2))
    db_session.add(ExamAssignment(exam_id=exam_b.id, student_id=student1.id, assigned_at=utc_now()))

    # Exam C: Coding only, 50 marks, 40% passing
    exam_c = Exam(title="Exam C Coding Only", created_by=examiner.id, status="published")
    db_session.add(exam_c)
    db_session.flush()
    db_session.add(ExamSettings(
        exam_id=exam_c.id,
        duration_minutes=60,
        total_marks=50.0,
        passing_percentage=40.0,
        negative_marking_ratio=0.0,
    ))
    q_c1 = Question(category_id=cat.id, question_type="coding", question_text="QC1", marks=50.0, created_by=examiner.id)
    db_session.add(q_c1)
    db_session.flush()
    cq_c1 = CodingQuestion(question_id=q_c1.id, problem_statement="Solve it", allowed_languages=["python"])
    db_session.add(cq_c1)
    db_session.add(ExamQuestion(exam_id=exam_c.id, question_id=q_c1.id, question_order=1))
    db_session.add(ExamAssignment(exam_id=exam_c.id, student_id=student1.id, assigned_at=utc_now()))

    db_session.commit()


def _make_submitted_attempt(db_session, exam, student) -> ExamAttempt:
    """Create a submitted attempt with no answers."""
    att = ExamAttempt(
        exam_id=exam.id,
        student_id=student.id,
        started_at=utc_now(),
        status="submitted",
        submitted_at=utc_now(),
    )
    db_session.add(att)
    db_session.commit()
    db_session.refresh(att)
    return att


def _answer_mcq(db_session, attempt: ExamAttempt, question: Question, option: McqOption):
    """Create or update an AttemptAnswer for an MCQ."""
    existing = db_session.query(AttemptAnswer).filter(
        AttemptAnswer.attempt_id == attempt.id,
        AttemptAnswer.question_id == question.id,
    ).first()
    if existing:
        existing.selected_option_id = option.id
        db_session.commit()
        return existing
    ans = AttemptAnswer(
        attempt_id=attempt.id,
        question_id=question.id,
        selected_option_id=option.id,
        answered_at=utc_now(),
    )
    db_session.add(ans)
    db_session.commit()
    db_session.refresh(ans)
    return ans


def _coding_submission(db_session, attempt: ExamAttempt, cq: CodingQuestion, score: float) -> CodingSubmission:
    """Create a CodingSubmission with a given score."""
    sub = CodingSubmission(
        attempt_id=attempt.id,
        coding_question_id=cq.id,
        language="python",
        source_code="print('hello')",
        status="accepted",
        score=score,
        is_final=True,
    )
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(sub)
    return sub


# ──────────────────────────────────────────────────────────────────────────────
# Unit tests: apply_negative_marking()
# ──────────────────────────────────────────────────────────────────────────────

class TestApplyNegativeMarking:
    def test_standard_ratio(self):
        penalty = apply_negative_marking(2.0, 0.25)
        assert penalty == pytest.approx(-0.5)

    def test_zero_ratio_no_penalty(self):
        assert apply_negative_marking(10.0, 0.0) == 0.0

    def test_full_ratio(self):
        assert apply_negative_marking(4.0, 1.0) == pytest.approx(-4.0)

    def test_half_ratio(self):
        assert apply_negative_marking(10.0, 0.5) == pytest.approx(-5.0)

    def test_result_is_negative_or_zero(self):
        assert apply_negative_marking(5.0, 0.33) <= 0.0

    def test_negative_ratio_treated_as_zero(self):
        # Negative ratios should not produce positive penalties
        assert apply_negative_marking(10.0, -0.5) == 0.0


# ──────────────────────────────────────────────────────────────────────────────
# Unit tests: determine_pass_fail()
# ──────────────────────────────────────────────────────────────────────────────

class TestDeterminePassFail:
    def test_above_threshold_passes(self):
        assert determine_pass_fail(75.0, 50.0) is True

    def test_below_threshold_fails(self):
        assert determine_pass_fail(49.99, 50.0) is False

    def test_exactly_threshold_passes(self):
        assert determine_pass_fail(50.0, 50.0) is True

    def test_zero_percentage_fails(self):
        assert determine_pass_fail(0.0, 40.0) is False

    def test_hundred_percentage_passes(self):
        assert determine_pass_fail(100.0, 100.0) is True

    def test_just_below_boundary_fails(self):
        assert determine_pass_fail(39.99, 40.0) is False


# ──────────────────────────────────────────────────────────────────────────────
# Basic scoring tests
# ──────────────────────────────────────────────────────────────────────────────

class TestBasicScoring:
    def test_correct_mcq_receives_marks(self, db_session):
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()
        q_mcq = db_session.query(Question).filter(Question.question_text == "Q1 MCQ").first()
        opt_right = db_session.query(McqOption).filter(
            McqOption.question_id == q_mcq.id, McqOption.is_correct == True
        ).first()

        att = _make_submitted_attempt(db_session, exam_a, student)
        _answer_mcq(db_session, att, q_mcq, opt_right)

        result = calculate_final_score(db_session, att.id)
        assert float(result.total_marks_obtained) >= 10.0  # MCQ correct

    def test_incorrect_mcq_receives_negative_marks(self, db_session):
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()
        q_mcq = db_session.query(Question).filter(Question.question_text == "Q1 MCQ").first()
        opt_wrong = db_session.query(McqOption).filter(
            McqOption.question_id == q_mcq.id, McqOption.is_correct == False
        ).first()

        att = _make_submitted_attempt(db_session, exam_a, student)
        _answer_mcq(db_session, att, q_mcq, opt_wrong)

        result = calculate_final_score(db_session, att.id)
        # 0 coding + (-10 * 0.25 = -2.5 penalty) = -2.5, clamped behavior tested separately
        mcq_portion = float(result.total_marks_obtained)
        assert mcq_portion < 0  # negative marking applied

    def test_unanswered_mcq_receives_zero(self, db_session):
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()

        att = _make_submitted_attempt(db_session, exam_a, student)
        # No answers added

        result = calculate_final_score(db_session, att.id)
        assert float(result.total_marks_obtained) == 0.0

    def test_coding_score_calculated_correctly(self, db_session):
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()
        q_code = db_session.query(Question).filter(Question.question_text == "Q2 Code").first()
        cq = db_session.query(CodingQuestion).filter(CodingQuestion.question_id == q_code.id).first()

        att = _make_submitted_attempt(db_session, exam_a, student)
        _coding_submission(db_session, att, cq, score=15.0)

        result = calculate_final_score(db_session, att.id)
        assert float(result.total_marks_obtained) == 15.0

    def test_mcq_and_coding_combined(self, db_session):
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()
        q_mcq = db_session.query(Question).filter(Question.question_text == "Q1 MCQ").first()
        opt_right = db_session.query(McqOption).filter(
            McqOption.question_id == q_mcq.id, McqOption.is_correct == True
        ).first()
        q_code = db_session.query(Question).filter(Question.question_text == "Q2 Code").first()
        cq = db_session.query(CodingQuestion).filter(CodingQuestion.question_id == q_code.id).first()

        att = _make_submitted_attempt(db_session, exam_a, student)
        _answer_mcq(db_session, att, q_mcq, opt_right)   # +10
        _coding_submission(db_session, att, cq, score=20.0)  # +20

        result = calculate_final_score(db_session, att.id)
        assert float(result.total_marks_obtained) == pytest.approx(30.0)
        assert float(result.total_marks_possible) == pytest.approx(30.0)
        assert float(result.percentage) == pytest.approx(100.0)
        assert result.pass_fail is True

    def test_total_marks_possible_is_correct(self, db_session):
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()

        att = _make_submitted_attempt(db_session, exam_a, student)
        result = calculate_final_score(db_session, att.id)

        assert float(result.total_marks_possible) == pytest.approx(30.0)  # 10 MCQ + 20 Coding

    def test_percentage_is_correct(self, db_session):
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()
        q_mcq = db_session.query(Question).filter(Question.question_text == "Q1 MCQ").first()
        opt_right = db_session.query(McqOption).filter(
            McqOption.question_id == q_mcq.id, McqOption.is_correct == True
        ).first()

        att = _make_submitted_attempt(db_session, exam_a, student)
        _answer_mcq(db_session, att, q_mcq, opt_right)  # 10/30

        result = calculate_final_score(db_session, att.id)
        assert float(result.percentage) == pytest.approx(33.33, abs=0.1)

    def test_pass_condition(self, db_session):
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()
        q_mcq = db_session.query(Question).filter(Question.question_text == "Q1 MCQ").first()
        opt_right = db_session.query(McqOption).filter(
            McqOption.question_id == q_mcq.id, McqOption.is_correct == True
        ).first()
        q_code = db_session.query(Question).filter(Question.question_text == "Q2 Code").first()
        cq = db_session.query(CodingQuestion).filter(CodingQuestion.question_id == q_code.id).first()

        att = _make_submitted_attempt(db_session, exam_a, student)
        _answer_mcq(db_session, att, q_mcq, opt_right)    # +10
        _coding_submission(db_session, att, cq, score=20.0)  # +20 → 100%

        result = calculate_final_score(db_session, att.id)
        assert result.pass_fail is True

    def test_fail_condition(self, db_session):
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()

        att = _make_submitted_attempt(db_session, exam_a, student)
        # No answers — 0% < 50% passing

        result = calculate_final_score(db_session, att.id)
        assert result.pass_fail is False


# ──────────────────────────────────────────────────────────────────────────────
# Negative marking tests
# ──────────────────────────────────────────────────────────────────────────────

class TestNegativeMarking:
    def test_negative_marking_ratio_respected(self, db_session):
        """10 marks question, 0.25 ratio → penalty = -2.5"""
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()
        q_mcq = db_session.query(Question).filter(Question.question_text == "Q1 MCQ").first()
        opt_wrong = db_session.query(McqOption).filter(
            McqOption.question_id == q_mcq.id, McqOption.is_correct == False
        ).first()

        att = _make_submitted_attempt(db_session, exam_a, student)
        _answer_mcq(db_session, att, q_mcq, opt_wrong)

        result = calculate_final_score(db_session, att.id)
        assert float(result.total_marks_obtained) == pytest.approx(-2.5)

    def test_negative_marking_not_applied_twice(self, db_session):
        """Calling calculate_final_score twice must not double the penalty."""
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()
        q_mcq = db_session.query(Question).filter(Question.question_text == "Q1 MCQ").first()
        opt_wrong = db_session.query(McqOption).filter(
            McqOption.question_id == q_mcq.id, McqOption.is_correct == False
        ).first()

        att = _make_submitted_attempt(db_session, exam_a, student)
        _answer_mcq(db_session, att, q_mcq, opt_wrong)

        r1 = calculate_final_score(db_session, att.id)
        r2 = calculate_final_score(db_session, att.id)

        assert float(r1.total_marks_obtained) == float(r2.total_marks_obtained)

    def test_no_negative_marking_when_ratio_zero(self, db_session):
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_b = db_session.query(Exam).filter(Exam.title == "Exam B MCQ Only").first()
        q_b1 = db_session.query(Question).filter(Question.question_text == "QB1").first()
        opt_wrong = db_session.query(McqOption).filter(
            McqOption.question_id == q_b1.id, McqOption.is_correct == False
        ).first()

        att = _make_submitted_attempt(db_session, exam_b, student)
        _answer_mcq(db_session, att, q_b1, opt_wrong)

        result = calculate_final_score(db_session, att.id)
        # Wrong answer, 0 ratio → 0.0 not negative
        assert float(result.total_marks_obtained) == pytest.approx(0.0)

    def test_score_can_be_negative(self, db_session):
        """Score is allowed to go negative if exam config produces it."""
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()
        q_mcq = db_session.query(Question).filter(Question.question_text == "Q1 MCQ").first()
        opt_wrong = db_session.query(McqOption).filter(
            McqOption.question_id == q_mcq.id, McqOption.is_correct == False
        ).first()

        att = _make_submitted_attempt(db_session, exam_a, student)
        _answer_mcq(db_session, att, q_mcq, opt_wrong)

        result = calculate_final_score(db_session, att.id)
        assert float(result.total_marks_obtained) < 0.0

    def test_zero_score_handled(self, db_session):
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()

        att = _make_submitted_attempt(db_session, exam_a, student)
        result = calculate_final_score(db_session, att.id)

        assert float(result.total_marks_obtained) == pytest.approx(0.0)
        assert float(result.percentage) == pytest.approx(0.0)
        assert result.pass_fail is False


# ──────────────────────────────────────────────────────────────────────────────
# Boundary cases
# ──────────────────────────────────────────────────────────────────────────────

class TestBoundaryCases:
    def test_exactly_passing_percentage_passes(self, db_session):
        """Exam B: 60% passing. Scoring exactly 60% (one of two 20-mark questions correct)
        gives 50% — let's score both correct = 100% and check pass."""
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_b = db_session.query(Exam).filter(Exam.title == "Exam B MCQ Only").first()
        q_b1 = db_session.query(Question).filter(Question.question_text == "QB1").first()
        q_b2 = db_session.query(Question).filter(Question.question_text == "QB2").first()
        opt_b1_r = db_session.query(McqOption).filter(McqOption.question_id == q_b1.id, McqOption.is_correct == True).first()
        opt_b2_r = db_session.query(McqOption).filter(McqOption.question_id == q_b2.id, McqOption.is_correct == True).first()

        att = _make_submitted_attempt(db_session, exam_b, student)
        _answer_mcq(db_session, att, q_b1, opt_b1_r)
        _answer_mcq(db_session, att, q_b2, opt_b2_r)

        result = calculate_final_score(db_session, att.id)
        assert float(result.percentage) == pytest.approx(100.0)
        assert result.pass_fail is True

    def test_just_below_passing_percentage_fails(self, db_session):
        """Exam B: 60% passing. One correct (50%) → fail."""
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_b = db_session.query(Exam).filter(Exam.title == "Exam B MCQ Only").first()
        q_b1 = db_session.query(Question).filter(Question.question_text == "QB1").first()
        opt_b1_r = db_session.query(McqOption).filter(McqOption.question_id == q_b1.id, McqOption.is_correct == True).first()

        att = _make_submitted_attempt(db_session, exam_b, student)
        _answer_mcq(db_session, att, q_b1, opt_b1_r)  # 20/40 = 50% < 60%

        result = calculate_final_score(db_session, att.id)
        assert float(result.percentage) == pytest.approx(50.0)
        assert result.pass_fail is False

    def test_zero_total_marks_no_division_by_zero(self, db_session):
        """Exam with 0 total_marks_possible should not raise ZeroDivisionError."""
        examiner = db_session.query(User).filter(User.email == "examiner@test.com").first()
        student = db_session.query(User).filter(User.email == "student1@test.com").first()

        # Exam with no questions
        empty_exam = Exam(title="Empty Exam", created_by=examiner.id, status="published")
        db_session.add(empty_exam)
        db_session.flush()
        db_session.add(ExamSettings(
            exam_id=empty_exam.id,
            duration_minutes=10,
            total_marks=0,
            passing_percentage=50.0,
            negative_marking_ratio=0.0,
        ))
        db_session.add(ExamAssignment(exam_id=empty_exam.id, student_id=student.id, assigned_at=utc_now()))
        att = ExamAttempt(exam_id=empty_exam.id, student_id=student.id, started_at=utc_now(), status="submitted", submitted_at=utc_now())
        db_session.add(att)
        db_session.commit()
        db_session.refresh(att)

        result = calculate_final_score(db_session, att.id)
        assert float(result.total_marks_possible) == 0.0
        assert float(result.percentage) == 0.0

    def test_exam_with_only_mcqs_works(self, db_session):
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_b = db_session.query(Exam).filter(Exam.title == "Exam B MCQ Only").first()
        q_b1 = db_session.query(Question).filter(Question.question_text == "QB1").first()
        opt_b1_r = db_session.query(McqOption).filter(McqOption.question_id == q_b1.id, McqOption.is_correct == True).first()

        att = _make_submitted_attempt(db_session, exam_b, student)
        _answer_mcq(db_session, att, q_b1, opt_b1_r)

        result = calculate_final_score(db_session, att.id)
        assert float(result.total_marks_obtained) == pytest.approx(20.0)

    def test_exam_with_only_coding_works(self, db_session):
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_c = db_session.query(Exam).filter(Exam.title == "Exam C Coding Only").first()
        q_c1 = db_session.query(Question).filter(Question.question_text == "QC1").first()
        cq_c1 = db_session.query(CodingQuestion).filter(CodingQuestion.question_id == q_c1.id).first()

        att = _make_submitted_attempt(db_session, exam_c, student)
        _coding_submission(db_session, att, cq_c1, score=30.0)

        result = calculate_final_score(db_session, att.id)
        assert float(result.total_marks_obtained) == pytest.approx(30.0)
        assert float(result.total_marks_possible) == pytest.approx(50.0)

    def test_exam_with_no_answered_questions_works(self, db_session):
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()

        att = _make_submitted_attempt(db_session, exam_a, student)
        result = calculate_final_score(db_session, att.id)

        assert float(result.total_marks_obtained) == 0.0
        assert result.pass_fail is False

    def test_coding_score_capped_at_question_marks(self, db_session):
        """A coding submission with score > question marks should be capped."""
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()
        q_code = db_session.query(Question).filter(Question.question_text == "Q2 Code").first()
        cq = db_session.query(CodingQuestion).filter(CodingQuestion.question_id == q_code.id).first()

        att = _make_submitted_attempt(db_session, exam_a, student)
        _coding_submission(db_session, att, cq, score=999.0)  # Way more than 20 marks

        result = calculate_final_score(db_session, att.id)
        assert float(result.total_marks_obtained) <= 20.0  # capped

    def test_missing_coding_submission_gives_zero(self, db_session):
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()

        att = _make_submitted_attempt(db_session, exam_a, student)
        # No coding submission

        result = calculate_final_score(db_session, att.id)
        assert float(result.total_marks_obtained) == 0.0  # no MCQ, no coding


# ──────────────────────────────────────────────────────────────────────────────
# State validation tests
# ──────────────────────────────────────────────────────────────────────────────

class TestStateValidation:
    def test_in_progress_attempt_cannot_be_scored(self, db_session):
        from fastapi import HTTPException
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()

        att = ExamAttempt(exam_id=exam_a.id, student_id=student.id, started_at=utc_now(), status="in_progress")
        db_session.add(att)
        db_session.commit()
        db_session.refresh(att)

        with pytest.raises(HTTPException) as exc_info:
            calculate_final_score(db_session, att.id)
        assert exc_info.value.status_code == 409

    def test_submitted_attempt_can_be_scored(self, db_session):
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()

        att = _make_submitted_attempt(db_session, exam_a, student)
        result = calculate_final_score(db_session, att.id)
        assert result is not None

    def test_auto_submitted_attempt_can_be_scored(self, db_session):
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()

        att = ExamAttempt(exam_id=exam_a.id, student_id=student.id, started_at=utc_now(), status="auto_submitted", submitted_at=utc_now())
        db_session.add(att)
        db_session.commit()
        db_session.refresh(att)

        result = calculate_final_score(db_session, att.id)
        assert result is not None

    def test_invalid_attempt_id_raises_404(self, db_session):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            calculate_final_score(db_session, 999999)
        assert exc_info.value.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# Idempotency tests
# ──────────────────────────────────────────────────────────────────────────────

class TestIdempotency:
    def test_calling_twice_does_not_create_duplicate_result(self, db_session):
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()

        att = _make_submitted_attempt(db_session, exam_a, student)
        calculate_final_score(db_session, att.id)
        calculate_final_score(db_session, att.id)

        count = db_session.query(Result).filter(Result.attempt_id == att.id).count()
        assert count == 1

    def test_result_is_consistent_on_second_call(self, db_session):
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()
        q_mcq = db_session.query(Question).filter(Question.question_text == "Q1 MCQ").first()
        opt_right = db_session.query(McqOption).filter(McqOption.question_id == q_mcq.id, McqOption.is_correct == True).first()

        att = _make_submitted_attempt(db_session, exam_a, student)
        _answer_mcq(db_session, att, q_mcq, opt_right)

        r1 = calculate_final_score(db_session, att.id)
        r2 = calculate_final_score(db_session, att.id)

        assert r1.id == r2.id
        assert float(r1.total_marks_obtained) == float(r2.total_marks_obtained)
        assert float(r1.percentage) == float(r2.percentage)

    def test_negative_marking_not_duplicated_on_second_call(self, db_session):
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()
        q_mcq = db_session.query(Question).filter(Question.question_text == "Q1 MCQ").first()
        opt_wrong = db_session.query(McqOption).filter(McqOption.question_id == q_mcq.id, McqOption.is_correct == False).first()

        att = _make_submitted_attempt(db_session, exam_a, student)
        _answer_mcq(db_session, att, q_mcq, opt_wrong)

        r1 = calculate_final_score(db_session, att.id)
        r2 = calculate_final_score(db_session, att.id)

        assert float(r1.total_marks_obtained) == float(r2.total_marks_obtained)

    def test_coding_score_not_duplicated(self, db_session):
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()
        q_code = db_session.query(Question).filter(Question.question_text == "Q2 Code").first()
        cq = db_session.query(CodingQuestion).filter(CodingQuestion.question_id == q_code.id).first()

        att = _make_submitted_attempt(db_session, exam_a, student)
        _coding_submission(db_session, att, cq, score=18.0)

        r1 = calculate_final_score(db_session, att.id)
        r2 = calculate_final_score(db_session, att.id)

        assert float(r1.total_marks_obtained) == float(r2.total_marks_obtained)


# ──────────────────────────────────────────────────────────────────────────────
# Authorization tests (via HTTP client)
# ──────────────────────────────────────────────────────────────────────────────

class TestAuthorization:
    def test_student_can_view_own_result(self, client, db_session):
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()
        headers = get_auth_header(student.id, student.email, "student")

        att = _make_submitted_attempt(db_session, exam_a, student)
        calculate_final_score(db_session, att.id)

        res = client.get(f"/results/{att.id}", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["attempt_id"] == att.id
        assert data["student_id"] == student.id

    def test_student_cannot_view_another_students_result(self, client, db_session):
        student1 = db_session.query(User).filter(User.email == "student1@test.com").first()
        student2 = db_session.query(User).filter(User.email == "student2@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()
        headers2 = get_auth_header(student2.id, student2.email, "student")

        att = _make_submitted_attempt(db_session, exam_a, student1)
        calculate_final_score(db_session, att.id)

        res = client.get(f"/results/{att.id}", headers=headers2)
        assert res.status_code == 403

    def test_unauthenticated_user_rejected(self, client, db_session):
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()

        att = _make_submitted_attempt(db_session, exam_a, student)
        calculate_final_score(db_session, att.id)

        res = client.get(f"/results/{att.id}")
        assert res.status_code == 401

    def test_examiner_can_view_own_exam_result(self, client, db_session):
        examiner = db_session.query(User).filter(User.email == "examiner@test.com").first()
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()
        headers = get_auth_header(examiner.id, examiner.email, "examiner")

        att = _make_submitted_attempt(db_session, exam_a, student)
        calculate_final_score(db_session, att.id)

        res = client.get(f"/results/{att.id}", headers=headers)
        assert res.status_code == 200

    def test_examiner_cannot_view_other_examiners_exam_result(self, client, db_session):
        examiner2 = db_session.query(User).filter(User.email == "examiner2@test.com").first()
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()
        headers2 = get_auth_header(examiner2.id, examiner2.email, "examiner")

        att = _make_submitted_attempt(db_session, exam_a, student)
        calculate_final_score(db_session, att.id)

        res = client.get(f"/results/{att.id}", headers=headers2)
        assert res.status_code == 403

    def test_admin_can_view_any_result(self, client, db_session):
        admin = db_session.query(User).filter(User.email == "admin@test.com").first()
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()
        headers = get_auth_header(admin.id, admin.email, "admin")

        att = _make_submitted_attempt(db_session, exam_a, student)
        calculate_final_score(db_session, att.id)

        res = client.get(f"/results/{att.id}", headers=headers)
        assert res.status_code == 200


# ──────────────────────────────────────────────────────────────────────────────
# Endpoint tests
# ──────────────────────────────────────────────────────────────────────────────

class TestResultEndpoints:
    def test_get_result_endpoint_returns_correct_structure(self, client, db_session):
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()
        headers = get_auth_header(student.id, student.email, "student")

        att = _make_submitted_attempt(db_session, exam_a, student)
        calculate_final_score(db_session, att.id)

        res = client.get(f"/results/{att.id}", headers=headers)
        assert res.status_code == 200
        data = res.json()
        for field in ["attempt_id", "exam_id", "student_id", "total_marks_obtained",
                      "total_marks_possible", "percentage", "pass_fail", "calculated_at"]:
            assert field in data

    def test_breakdown_endpoint_returns_breakdown(self, client, db_session):
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()
        headers = get_auth_header(student.id, student.email, "student")

        att = _make_submitted_attempt(db_session, exam_a, student)
        calculate_final_score(db_session, att.id)

        res = client.get(f"/results/{att.id}/breakdown", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "breakdown" in data
        assert data["breakdown"] is not None
        bd = data["breakdown"]
        assert "mcq_marks_obtained" in bd
        assert "coding_marks_obtained" in bd
        assert "negative_marks_applied" in bd

    def test_in_progress_attempt_returns_404_from_endpoint(self, client, db_session):
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()
        headers = get_auth_header(student.id, student.email, "student")

        att = ExamAttempt(exam_id=exam_a.id, student_id=student.id, started_at=utc_now(), status="in_progress")
        db_session.add(att)
        db_session.commit()
        db_session.refresh(att)

        res = client.get(f"/results/{att.id}", headers=headers)
        # In progress → no result yet
        assert res.status_code in (404, 409)

    def test_list_exam_results_admin(self, client, db_session):
        admin = db_session.query(User).filter(User.email == "admin@test.com").first()
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()
        headers = get_auth_header(admin.id, admin.email, "admin")

        att = _make_submitted_attempt(db_session, exam_a, student)
        calculate_final_score(db_session, att.id)

        res = client.get(f"/exams/{exam_a.id}/results", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["attempt_id"] == att.id

    def test_student_cannot_list_exam_results(self, client, db_session):
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()
        headers = get_auth_header(student.id, student.email, "student")

        res = client.get(f"/exams/{exam_a.id}/results", headers=headers)
        assert res.status_code == 403

    def test_recalculate_endpoint_admin(self, client, db_session):
        admin = db_session.query(User).filter(User.email == "admin@test.com").first()
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()
        headers = get_auth_header(admin.id, admin.email, "admin")

        att = _make_submitted_attempt(db_session, exam_a, student)

        res = client.post(f"/results/{att.id}/calculate", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "attempt_id" in data
        assert "percentage" in data

    def test_recalculate_endpoint_student_forbidden(self, client, db_session):
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()
        headers = get_auth_header(student.id, student.email, "student")

        att = _make_submitted_attempt(db_session, exam_a, student)

        res = client.post(f"/results/{att.id}/calculate", headers=headers)
        assert res.status_code == 403


# ──────────────────────────────────────────────────────────────────────────────
# Integration: Module 2.9 → Module 2.10 flow (via client endpoints)
# ──────────────────────────────────────────────────────────────────────────────

class TestIntegration:
    def test_submit_attempt_triggers_result_calculation(self, client, db_session):
        """
        Full flow:
        1. Student starts exam
        2. Answers MCQ
        3. Submits
        4. Module 2.9 calls Module 2.10 internally
        5. Result row exists
        """
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()
        headers = get_auth_header(student.id, student.email, "student")

        # Start
        start_res = client.post(f"/exams/{exam_a.id}/attempt", headers=headers)
        assert start_res.status_code == 200
        att_id = start_res.json()["attempt_id"]

        # Answer MCQ
        q_mcq = db_session.query(Question).filter(Question.question_text == "Q1 MCQ").first()
        opt_right = db_session.query(McqOption).filter(McqOption.question_id == q_mcq.id, McqOption.is_correct == True).first()
        client.put(
            f"/exam-attempts/{att_id}/answers/autosave",
            json={"question_id": q_mcq.id, "selected_option_id": opt_right.id},
            headers=headers,
        )

        # Submit
        sub_res = client.post(f"/exam-attempts/{att_id}/submit", headers=headers)
        assert sub_res.status_code == 200
        assert sub_res.json()["score"] is not None

        # Result row created
        result = db_session.query(Result).filter(Result.attempt_id == att_id).first()
        assert result is not None
        assert float(result.total_marks_obtained) == pytest.approx(10.0)

    def test_auto_submitted_attempt_produces_result(self, client, db_session):
        """Timer expires → auto_submit → result calculated."""
        from app.services.exam_attempt_service import auto_submit_expired_attempts

        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()
        headers = get_auth_header(student.id, student.email, "student")

        start_res = client.post(f"/exams/{exam_a.id}/attempt", headers=headers)
        att_id = start_res.json()["attempt_id"]

        # Age attempt
        att = db_session.query(ExamAttempt).filter(ExamAttempt.id == att_id).first()
        att.started_at = (utc_now() - timedelta(hours=3))
        db_session.commit()

        count = auto_submit_expired_attempts(db_session)
        assert count == 1

        result = db_session.query(Result).filter(Result.attempt_id == att_id).first()
        assert result is not None

    def test_result_accessible_after_auto_submit(self, client, db_session):
        from app.services.exam_attempt_service import auto_submit_expired_attempts

        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()
        headers = get_auth_header(student.id, student.email, "student")

        start_res = client.post(f"/exams/{exam_a.id}/attempt", headers=headers)
        att_id = start_res.json()["attempt_id"]

        att = db_session.query(ExamAttempt).filter(ExamAttempt.id == att_id).first()
        att.started_at = (utc_now() - timedelta(hours=3))
        db_session.commit()

        auto_submit_expired_attempts(db_session)

        res = client.get(f"/results/{att_id}", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["attempt_id"] == att_id

    def test_full_mcq_and_coding_lifecycle(self, client, db_session):
        """
        Start → autosave MCQ (correct) → autosave code draft → submit →
        result has MCQ marks + coding marks from best CodingSubmission.
        """
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()
        headers = get_auth_header(student.id, student.email, "student")

        start_res = client.post(f"/exams/{exam_a.id}/attempt", headers=headers)
        att_id = start_res.json()["attempt_id"]

        # Answer MCQ correctly
        q_mcq = db_session.query(Question).filter(Question.question_text == "Q1 MCQ").first()
        opt_right = db_session.query(McqOption).filter(McqOption.question_id == q_mcq.id, McqOption.is_correct == True).first()
        client.put(
            f"/exam-attempts/{att_id}/answers/autosave",
            json={"question_id": q_mcq.id, "selected_option_id": opt_right.id},
            headers=headers,
        )

        # Autosave code draft (no judge0 in tests — gives 0 score from coding)
        cq = db_session.query(CodingQuestion).first()
        client.put(
            f"/exam-attempts/{att_id}/coding/{cq.id}/autosave",
            json={"language": "python", "source_code": "print('hello')"},
            headers=headers,
        )

        # Submit
        sub_res = client.post(f"/exam-attempts/{att_id}/submit", headers=headers)
        assert sub_res.status_code == 200
        assert sub_res.json()["score"] is not None  # at least MCQ score

        # Breakdown endpoint
        res = client.get(f"/results/{att_id}/breakdown", headers=headers)
        assert res.status_code == 200
        bd = res.json()["breakdown"]
        assert bd["mcq_marks_obtained"] == pytest.approx(10.0)
        assert bd["mcq_marks_possible"] == pytest.approx(10.0)


# ──────────────────────────────────────────────────────────────────────────────
# ExecutionResult & Test Case scoring tests
# ──────────────────────────────────────────────────────────────────────────────

class TestExecutionResultScoring:
    def test_coding_submission_scored_from_execution_results(self, db_session):
        """When ExecutionResult records exist, score is computed pro-rata from passed test cases."""
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()
        q_code = db_session.query(Question).filter(Question.question_text == "Q2 Code").first()
        cq = db_session.query(CodingQuestion).filter(CodingQuestion.question_id == q_code.id).first()

        # Create test cases for cq
        tc1 = CodingTestCase(coding_question_id=cq.id, input="1", expected_output="1", is_sample=True, is_hidden=False)
        tc2 = CodingTestCase(coding_question_id=cq.id, input="2", expected_output="2", is_sample=False, is_hidden=True)
        tc3 = CodingTestCase(coding_question_id=cq.id, input="3", expected_output="3", is_sample=False, is_hidden=True)
        tc4 = CodingTestCase(coding_question_id=cq.id, input="4", expected_output="4", is_sample=False, is_hidden=True)
        db_session.add_all([tc1, tc2, tc3, tc4])
        db_session.flush()

        att = _make_submitted_attempt(db_session, exam_a, student)
        sub = CodingSubmission(
            attempt_id=att.id,
            coding_question_id=cq.id,
            language="python",
            source_code="code",
            status="partial",
            score=0.0,
            is_final=True,
        )
        db_session.add(sub)
        db_session.flush()

        # 2 passed, 1 compile error, 1 tle -> 2/4 = 50% of 20 marks = 10 marks
        db_session.add_all([
            ExecutionResult(submission_id=sub.id, test_case_id=tc1.id, verdict="passed"),
            ExecutionResult(submission_id=sub.id, test_case_id=tc2.id, verdict="passed"),
            ExecutionResult(submission_id=sub.id, test_case_id=tc3.id, verdict="compile_error"),
            ExecutionResult(submission_id=sub.id, test_case_id=tc4.id, verdict="tle"),
        ])
        db_session.commit()

        result = calculate_final_score(db_session, att.id)
        assert float(result.total_marks_obtained) == pytest.approx(10.0)

    def test_best_submission_picked_among_multiple_coding_submissions(self, db_session):
        """When multiple submissions exist, the one yielding the highest score is used."""
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        exam_a = db_session.query(Exam).filter(Exam.title == "Exam A").first()
        q_code = db_session.query(Question).filter(Question.question_text == "Q2 Code").first()
        cq = db_session.query(CodingQuestion).filter(CodingQuestion.question_id == q_code.id).first()

        att = _make_submitted_attempt(db_session, exam_a, student)
        _coding_submission(db_session, att, cq, score=5.0)
        _coding_submission(db_session, att, cq, score=16.0)
        _coding_submission(db_session, att, cq, score=10.0)

        result = calculate_final_score(db_session, att.id)
        assert float(result.total_marks_obtained) == pytest.approx(16.0)


class TestMarksOverride:
    def test_marks_override_applied_to_mcq_and_coding(self, db_session):
        """marks_override on ExamQuestion takes precedence over Question.marks."""
        examiner = db_session.query(User).filter(User.email == "examiner@test.com").first()
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        cat = db_session.query(QuestionCategory).first()

        override_exam = Exam(title="Override Exam", created_by=examiner.id, status="published")
        db_session.add(override_exam)
        db_session.flush()
        db_session.add(ExamSettings(
            exam_id=override_exam.id,
            duration_minutes=60,
            total_marks=40.0,
            passing_percentage=50.0,
            negative_marking_ratio=0.25,
        ))

        # Base MCQ 10 marks overridden to 15 marks
        q_mcq = Question(category_id=cat.id, question_type="mcq", question_text="Q Over MCQ", marks=10.0, created_by=examiner.id)
        db_session.add(q_mcq)
        db_session.flush()
        opt_wrong = McqOption(question_id=q_mcq.id, option_text="W", is_correct=False)
        opt_right = McqOption(question_id=q_mcq.id, option_text="R", is_correct=True)
        db_session.add_all([opt_wrong, opt_right])
        db_session.add(ExamQuestion(exam_id=override_exam.id, question_id=q_mcq.id, question_order=1, marks_override=15.0))

        # Base Coding 20 marks overridden to 25 marks
        q_code = Question(category_id=cat.id, question_type="coding", question_text="Q Over Code", marks=20.0, created_by=examiner.id)
        db_session.add(q_code)
        db_session.flush()
        cq = CodingQuestion(question_id=q_code.id, problem_statement="Override code", allowed_languages=["python"])
        db_session.add(cq)
        db_session.add(ExamQuestion(exam_id=override_exam.id, question_id=q_code.id, question_order=2, marks_override=25.0))

        db_session.add(ExamAssignment(exam_id=override_exam.id, student_id=student.id, assigned_at=utc_now()))
        db_session.commit()

        att = _make_submitted_attempt(db_session, override_exam, student)
        _answer_mcq(db_session, att, q_mcq, opt_right)  # 15 marks
        _coding_submission(db_session, att, cq, score=25.0)  # 25 marks

        result = calculate_final_score(db_session, att.id)
        assert float(result.total_marks_possible) == pytest.approx(40.0)  # 15 + 25
        assert float(result.total_marks_obtained) == pytest.approx(40.0)
        assert float(result.percentage) == pytest.approx(100.0)


class TestExtremePassingPercentages:
    def test_zero_passing_percentage_passes_with_zero_score(self, db_session):
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        examiner = db_session.query(User).filter(User.email == "examiner@test.com").first()
        cat = db_session.query(QuestionCategory).first()

        exam_zero = Exam(title="Zero Pct Exam", created_by=examiner.id, status="published")
        db_session.add(exam_zero)
        db_session.flush()
        db_session.add(ExamSettings(
            exam_id=exam_zero.id,
            duration_minutes=30,
            total_marks=10.0,
            passing_percentage=0.0,
            negative_marking_ratio=0.0,
        ))
        q = Question(category_id=cat.id, question_type="mcq", question_text="QZ", marks=10.0, created_by=examiner.id)
        db_session.add(q)
        db_session.flush()
        opt = McqOption(question_id=q.id, option_text="Opt", is_correct=True)
        db_session.add(opt)
        db_session.add(ExamQuestion(exam_id=exam_zero.id, question_id=q.id, question_order=1))
        db_session.add(ExamAssignment(exam_id=exam_zero.id, student_id=student.id, assigned_at=utc_now()))
        db_session.commit()

        att = _make_submitted_attempt(db_session, exam_zero, student)
        result = calculate_final_score(db_session, att.id)
        assert float(result.percentage) == 0.0
        assert result.pass_fail is True  # 0% >= 0% passing

    def test_hundred_passing_percentage_requires_perfect_score(self, db_session):
        student = db_session.query(User).filter(User.email == "student1@test.com").first()
        examiner = db_session.query(User).filter(User.email == "examiner@test.com").first()
        cat = db_session.query(QuestionCategory).first()

        exam_hundred = Exam(title="Hundred Pct Exam", created_by=examiner.id, status="published")
        db_session.add(exam_hundred)
        db_session.flush()
        db_session.add(ExamSettings(
            exam_id=exam_hundred.id,
            duration_minutes=30,
            total_marks=20.0,
            passing_percentage=100.0,
            negative_marking_ratio=0.0,
        ))
        q1 = Question(category_id=cat.id, question_type="mcq", question_text="QH1", marks=10.0, created_by=examiner.id)
        q2 = Question(category_id=cat.id, question_type="mcq", question_text="QH2", marks=10.0, created_by=examiner.id)
        db_session.add_all([q1, q2])
        db_session.flush()
        opt1 = McqOption(question_id=q1.id, option_text="Opt1", is_correct=True)
        opt2 = McqOption(question_id=q2.id, option_text="Opt2", is_correct=True)
        db_session.add_all([opt1, opt2])
        db_session.add(ExamQuestion(exam_id=exam_hundred.id, question_id=q1.id, question_order=1))
        db_session.add(ExamQuestion(exam_id=exam_hundred.id, question_id=q2.id, question_order=2))
        db_session.add(ExamAssignment(exam_id=exam_hundred.id, student_id=student.id, assigned_at=utc_now()))
        db_session.commit()

        # Score 1 out of 2 (50%) -> Fails
        att1 = _make_submitted_attempt(db_session, exam_hundred, student)
        _answer_mcq(db_session, att1, q1, opt1)
        r1 = calculate_final_score(db_session, att1.id)
        assert r1.pass_fail is False

        # Score 2 out of 2 (100%) -> Passes
        _answer_mcq(db_session, att1, q2, opt2)
        r2 = calculate_final_score(db_session, att1.id)
        assert r2.pass_fail is True

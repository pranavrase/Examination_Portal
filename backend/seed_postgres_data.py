import sys
import os
from datetime import datetime, timedelta, timezone

# Add backend root directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.core.security import get_password_hash

# Import all ORM models
from app.models.role import Role
from app.models.user import User
from app.models.question import McqOption
from app.models.activity import LoginSession
from app.models.question import QuestionCategory, Question, McqOption, CodingQuestion, CodingTestCase, ExamQuestion
from app.models.exam import Exam, ExamSettings, ExamAssignment
from app.models.attempt import ExamAttempt, AttemptAnswer
from app.models.result import Result, Ranking
from app.models.log import ActivityLog
from app.models.notification import Notification

def seed_database():
    print("=" * 60)
    print("Seeding PostgreSQL Database (exam_portal_db)...")
    print("=" * 60)

    # Drop and recreate schema public CASCADE for clean PostgreSQL initialization
    with engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT")
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))

    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        # 1. Seed Roles
        role_names = ["admin", "examiner", "student"]
        roles_dict = {}
        for r_name in role_names:
            role = db.query(Role).filter(Role.name == r_name).first()
            if not role:
                role = Role(name=r_name)
                db.add(role)
                db.flush()
            roles_dict[r_name] = role
        db.commit()
        print("[SUCCESS] Roles checked/created.")

        # 2. Seed Users
        users_data = [
            {"email": "admin@examportal.com", "name": "System Admin", "role": "admin"},
            {"email": "pachpolsanket72@gmail.com", "name": "Sanket Pachpol", "role": "examiner"},
            {"email": "examiner@examportal.com", "name": "Dr. Sarah Jenkins", "role": "examiner"},
            {"email": "sanketpachpol229@gmail.com", "name": "Student Sanket", "role": "student", "roll_number": "CS2026-0004", "college": "Computer Science & Engineering"},
            {"email": "student@examportal.com", "name": "John Doe", "role": "student", "roll_number": "CS2026-0005", "college": "Computer Science & Engineering"},
            {"email": "emily.davis@university.edu", "name": "Emily Davis", "role": "student", "roll_number": "CS2026-0006", "college": "Computer Science & Engineering"},
            {"email": "rahul.kumar@example.com", "name": "Rahul Kumar", "role": "student", "roll_number": "CS2026-0007", "college": "Computer Science & Engineering"},
            {"email": "sneha.singh@example.com", "name": "Sneha Singh", "role": "student", "roll_number": "CS2026-0008", "college": "Computer Science & Engineering"},
        ]

        users_dict = {}
        pwd_hash = get_password_hash("Password123!")

        for udata in users_data:
            user = db.query(User).filter(User.email == udata["email"]).first()
            if not user:
                user = User(
                    email=udata["email"],
                    password_hash=pwd_hash,
                    full_name=udata["name"],
                    roll_number=udata.get("roll_number"),
                    college=udata.get("college"),
                    is_active=True,
                    is_verified=True,
                )
                user.roles.append(roles_dict[udata["role"]])
                db.add(user)
                db.flush()
            else:
                user.full_name = udata["name"]
                user.password_hash = pwd_hash
                if "roll_number" in udata:
                    user.roll_number = udata["roll_number"]
                if "college" in udata:
                    user.college = udata["college"]
                if roles_dict[udata["role"]] not in user.roles:
                    user.roles.append(roles_dict[udata["role"]])
            users_dict[udata["email"]] = user
        db.commit()
        print("[SUCCESS] Users checked/created.")

        admin_user = users_dict["admin@examportal.com"]
        examiner_user = users_dict["pachpolsanket72@gmail.com"]
        student_user1 = users_dict["sanketpachpol229@gmail.com"]
        student_user2 = users_dict["student@examportal.com"]

        # 3. Seed Question Categories
        categories_data = [
            {"name": "Data Structures & Algorithms", "topic": "DSA", "difficulty": "Medium"},
            {"name": "Web Development & APIs", "topic": "Web Dev", "difficulty": "Easy"},
            {"name": "Python & Logic", "topic": "Python", "difficulty": "Easy"},
            {"name": "Database Systems & SQL", "topic": "Databases", "difficulty": "Medium"},
        ]

        cat_dict = {}
        for cdata in categories_data:
            cat = db.query(QuestionCategory).filter(QuestionCategory.name == cdata["name"]).first()
            if not cat:
                cat = QuestionCategory(**cdata)
                db.add(cat)
                db.flush()
            cat_dict[cdata["name"]] = cat
        db.commit()
        print("[SUCCESS] Question Categories checked/created.")

        # 4. Seed Questions
        # Question 1: MCQ DSA
        q1 = db.query(Question).filter(Question.question_text.like("%worst-case time complexity of QuickSort%")).first()
        if not q1:
            q1 = Question(
                category_id=cat_dict["Data Structures & Algorithms"].id,
                question_type="mcq",
                question_text="What is the worst-case time complexity of QuickSort algorithm?",
                marks=5,
                created_by=examiner_user.id
            )
            db.add(q1)
            db.flush()
            mcq_opts = [
                McqOption(question_id=q1.id, option_text="O(n log n)", is_correct=False),
                McqOption(question_id=q1.id, option_text="O(n^2)", is_correct=True),
                McqOption(question_id=q1.id, option_text="O(n)", is_correct=False),
                McqOption(question_id=q1.id, option_text="O(log n)", is_correct=False),
            ]
            db.add_all(mcq_opts)

        # Question 2: MCQ Web Dev
        q2 = db.query(Question).filter(Question.question_text.like("%HTTP status code for Created%")).first()
        if not q2:
            q2 = Question(
                category_id=cat_dict["Web Development & APIs"].id,
                question_type="mcq",
                question_text="Which HTTP status code represents successful resource creation?",
                marks=5,
                created_by=examiner_user.id
            )
            db.add(q2)
            db.flush()
            mcq_opts2 = [
                McqOption(question_id=q2.id, option_text="200 OK", is_correct=False),
                McqOption(question_id=q2.id, option_text="201 Created", is_correct=True),
                McqOption(question_id=q2.id, option_text="204 No Content", is_correct=False),
                McqOption(question_id=q2.id, option_text="400 Bad Request", is_correct=False),
            ]
            db.add_all(mcq_opts2)

        # Question 3: Coding Question (Two Sum)
        q3 = db.query(Question).filter(Question.question_text.like("%Two Sum%")).first()
        if not q3:
            q3 = Question(
                category_id=cat_dict["Data Structures & Algorithms"].id,
                question_type="coding",
                question_text="Two Sum Problem: Find indices of two numbers that add up to target.",
                marks=20,
                created_by=examiner_user.id
            )
            db.add(q3)
            db.flush()
            coding_detail = CodingQuestion(
                question_id=q3.id,
                problem_statement="Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.",
                constraints="2 <= nums.length <= 10^4\n-10^9 <= nums[i] <= 10^9",
                allowed_languages=["python", "cpp", "java", "javascript"],
                time_limit_ms=2000,
                memory_limit_kb=256000
            )
            db.add(coding_detail)
            db.flush()

            tc1 = CodingTestCase(
                coding_question_id=coding_detail.id,
                input="4\n2 7 11 15\n9",
                expected_output="0 1",
                is_sample=True,
                is_hidden=False
            )
            tc2 = CodingTestCase(
                coding_question_id=coding_detail.id,
                input="3\n3 2 4\n6",
                expected_output="1 2",
                is_sample=False,
                is_hidden=True
            )
            db.add_all([tc1, tc2])

        db.commit()
        print("[SUCCESS] Questions checked/created.")

        # 5. Seed Exams
        exam1 = db.query(Exam).filter(Exam.title == "Advanced Data Structures & Algorithms Assessment").first()
        if not exam1:
            exam1 = Exam(
                title="Advanced Data Structures & Algorithms Assessment",
                description="Comprehensive examination testing algorithmic proficiency, complexity analysis, and coding abilities.",
                created_by=examiner_user.id,
                status="published"
            )
            db.add(exam1)
            db.flush()

            settings1 = ExamSettings(
                exam_id=exam1.id,
                duration_minutes=60,
                total_marks=100,
                passing_percentage=40,
                negative_marking_ratio=0.25,
                randomize_questions=False,
                randomize_options=False
            )
            db.add(settings1)

            # Link questions
            eq1 = ExamQuestion(exam_id=exam1.id, question_id=q1.id, question_order=1)
            eq2 = ExamQuestion(exam_id=exam1.id, question_id=q2.id, question_order=2)
            eq3 = ExamQuestion(exam_id=exam1.id, question_id=q3.id, question_order=3)
            db.add_all([eq1, eq2, eq3])

        exam2 = db.query(Exam).filter(Exam.title == "Full Stack Web Development & Database Exam").first()
        if not exam2:
            exam2 = Exam(
                title="Full Stack Web Development & Database Exam",
                description="Assessment covering RESTful APIs, database schema design, and frontend integration.",
                created_by=examiner_user.id,
                status="published"
            )
            db.add(exam2)
            db.flush()

            settings2 = ExamSettings(
                exam_id=exam2.id,
                duration_minutes=90,
                total_marks=100,
                passing_percentage=50,
                negative_marking_ratio=0.0,
                randomize_questions=True,
                randomize_options=True
            )
            db.add(settings2)

            eq2_1 = ExamQuestion(exam_id=exam2.id, question_id=q2.id, question_order=1)
            db.add(eq2_1)

        db.commit()
        print("[SUCCESS] Exams checked/created.")

        # 6. Seed Exam Assignments
        for st in [student_user1, student_user2]:
            ass1 = db.query(ExamAssignment).filter(ExamAssignment.exam_id == exam1.id, ExamAssignment.student_id == st.id).first()
            if not ass1:
                ass1 = ExamAssignment(
                    exam_id=exam1.id,
                    student_id=st.id,
                    scheduled_start=datetime.now(timezone.utc) - timedelta(hours=1),
                    scheduled_end=datetime.now(timezone.utc) + timedelta(days=7)
                )
                db.add(ass1)

            ass2 = db.query(ExamAssignment).filter(ExamAssignment.exam_id == exam2.id, ExamAssignment.student_id == st.id).first()
            if not ass2:
                ass2 = ExamAssignment(
                    exam_id=exam2.id,
                    student_id=st.id,
                    scheduled_start=datetime.now(timezone.utc) - timedelta(hours=2),
                    scheduled_end=datetime.now(timezone.utc) + timedelta(days=14)
                )
                db.add(ass2)

        db.commit()
        print("[SUCCESS] Exam Assignments checked/created.")

        # 7. Seed Exam Attempt & Result for student_user1
        attempt1 = db.query(ExamAttempt).filter(ExamAttempt.exam_id == exam1.id, ExamAttempt.student_id == student_user1.id).first()
        if not attempt1:
            attempt1 = ExamAttempt(
                exam_id=exam1.id,
                student_id=student_user1.id,
                status="submitted",
                started_at=datetime.now(timezone.utc) - timedelta(days=1, hours=2),
                submitted_at=datetime.now(timezone.utc) - timedelta(days=1, hours=1)
            )
            db.add(attempt1)
            db.flush()

            res1 = Result(
                attempt_id=attempt1.id,
                total_marks_obtained=85.0,
                total_marks_possible=100.0,
                percentage=85.0,
                pass_fail=True
            )
            db.add(res1)
            db.flush()

            rnk1 = Ranking(
                exam_id=exam1.id,
                student_id=student_user1.id,
                rank=1,
                score=85.0
            )
            db.add(rnk1)

            # Add more sample students and results for testing
            student_role = db.query(Role).filter(Role.name == "student").first()
            
            # Use existing users from the main users section
            student_user2 = db.query(User).filter(User.email == "rahul.kumar@example.com").first()
            if not student_user2:
                student_user2 = User(
                    full_name="Rahul Kumar",
                    email="rahul.kumar@example.com",
                    password_hash=get_password_hash("student123"),
                    roll_number="CS2026-0007",
                    college="Computer Science & Engineering",
                    is_active=True,
                    is_verified=True,
                )
                student_user2.roles.append(student_role)
                db.add(student_user2)
                db.flush()

            attempt2 = ExamAttempt(
                exam_id=exam1.id,
                student_id=student_user2.id,
                status="submitted",
                started_at=datetime.now(timezone.utc) - timedelta(days=1, hours=3),
                submitted_at=datetime.now(timezone.utc) - timedelta(days=1, hours=2)
            )
            db.add(attempt2)
            db.flush()

            res2 = Result(
                attempt_id=attempt2.id,
                total_marks_obtained=72.0,
                total_marks_possible=100.0,
                percentage=72.0,
                pass_fail=True
            )
            db.add(res2)
            db.flush()

            rnk2 = Ranking(
                exam_id=exam1.id,
                student_id=student_user2.id,
                rank=2,
                score=72.0
            )
            db.add(rnk2)

            # Third student (failed)
            student_user3 = db.query(User).filter(User.email == "sneha.singh@example.com").first()
            if not student_user3:
                student_user3 = User(
                    full_name="Sneha Singh",
                    email="sneha.singh@example.com",
                    password_hash=get_password_hash("student123"),
                    roll_number="CS2026-0008",
                    college="Computer Science & Engineering",
                    is_active=True,
                    is_verified=True,
                )
                student_user3.roles.append(student_role)
                db.add(student_user3)
                db.flush()

            attempt3 = ExamAttempt(
                exam_id=exam1.id,
                student_id=student_user3.id,
                status="submitted",
                started_at=datetime.now(timezone.utc) - timedelta(days=1, hours=4),
                submitted_at=datetime.now(timezone.utc) - timedelta(days=1, hours=3)
            )
            db.add(attempt3)
            db.flush()

            res3 = Result(
                attempt_id=attempt3.id,
                total_marks_obtained=38.0,
                total_marks_possible=100.0,
                percentage=38.0,
                pass_fail=False
            )
            db.add(res3)
            db.flush()

            rnk3 = Ranking(
                exam_id=exam1.id,
                student_id=student_user3.id,
                rank=3,
                score=38.0
            )
            db.add(rnk3)

            # Add sample attempt answers for performance analysis
            # Get MCQ options for the questions
            q1_opts = db.query(McqOption).filter(McqOption.question_id == q1.id).all()
            q2_opts = db.query(McqOption).filter(McqOption.question_id == q2.id).all()
            
            # Student 1 answers (high performer)
            ans1 = AttemptAnswer(
                attempt_id=attempt1.id,
                question_id=q1.id,
                selected_option_id=q1_opts[1].id if len(q1_opts) > 1 else None,  # Correct answer
                is_correct=True,
                marks_awarded=5.0,
                answered_at=datetime.now(timezone.utc) - timedelta(days=1, hours=1, minutes=50)
            )
            db.add(ans1)
            
            ans2 = AttemptAnswer(
                attempt_id=attempt1.id,
                question_id=q2.id,
                selected_option_id=q2_opts[1].id if len(q2_opts) > 1 else None,  # Correct answer
                is_correct=True,
                marks_awarded=5.0,
                answered_at=datetime.now(timezone.utc) - timedelta(days=1, hours=1, minutes=30)
            )
            db.add(ans2)
            
            # Student 2 answers (medium performer)
            ans3 = AttemptAnswer(
                attempt_id=attempt2.id,
                question_id=q1.id,
                selected_option_id=q1_opts[0].id if len(q1_opts) > 0 else None,  # Wrong answer
                is_correct=False,
                marks_awarded=0.0,
                answered_at=datetime.now(timezone.utc) - timedelta(days=1, hours=2, minutes=40)
            )
            db.add(ans3)
            
            ans4 = AttemptAnswer(
                attempt_id=attempt2.id,
                question_id=q2.id,
                selected_option_id=q2_opts[0].id if len(q2_opts) > 0 else None,  # Wrong answer
                is_correct=False,
                marks_awarded=0.0,
                answered_at=datetime.now(timezone.utc) - timedelta(days=1, hours=2, minutes=20)
            )
            db.add(ans4)
            
            # Student 3 answers (low performer)
            ans5 = AttemptAnswer(
                attempt_id=attempt3.id,
                question_id=q1.id,
                selected_option_id=q1_opts[2].id if len(q1_opts) > 2 else None,  # Wrong answer
                is_correct=False,
                marks_awarded=0.0,
                answered_at=datetime.now(timezone.utc) - timedelta(days=1, hours=3, minutes=30)
            )
            db.add(ans5)
            
            ans6 = AttemptAnswer(
                attempt_id=attempt3.id,
                question_id=q2.id,
                selected_option_id=q2_opts[2].id if len(q2_opts) > 2 else None,  # Wrong answer
                is_correct=False,
                marks_awarded=0.0,
                answered_at=datetime.now(timezone.utc) - timedelta(days=1, hours=3, minutes=10)
            )
            db.add(ans6)
            
        db.commit()
        print("[SUCCESS] Exam Attempts and Results checked/created.")

        # 8. Seed Activity Logs & Notifications
        log1 = ActivityLog(
            user_id=admin_user.id,
            action_type="system",
            description="Database populated with live PostgreSQL data.",
            ip_address="127.0.0.1"
        )
        log2 = ActivityLog(
            user_id=examiner_user.id,
            action_type="exam_published",
            description=f"Published exam '{exam1.title}'",
            ip_address="127.0.0.1"
        )
        db.add_all([log1, log2])

        notif = Notification(
            user_id=student_user1.id,
            title="New Exam Assigned",
            message=f"You have been assigned to '{exam1.title}'.",
            notification_type="EXAM_PUBLISHED",
            is_read=False
        )
        db.add(notif)

        db.commit()
        print("[SUCCESS] Activity Logs and Notifications checked/created.")
        print("\nSUCCESS: All live PostgreSQL data seeded cleanly!")

    except Exception as e:
        db.rollback()
        print(f"ERROR Seeding database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()

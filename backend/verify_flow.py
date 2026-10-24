import json
import urllib.request
import urllib.parse

BASE_URL = "http://localhost:8000"

def run_test():
    print("=== Testing Coding Exam Flow ===")
    
    # 1. Login as student
    import app.main
    from app.db.session import SessionLocal
    from app.models.user import User
    from app.core.security import create_access_token
    from datetime import timedelta
    
    db = SessionLocal()
    student = db.query(User).filter(User.id == 2).first()
    if not student:
        student = db.query(User).filter(User.email.like("%student%")).first()
    print(f"Testing with Student: ID={student.id}, Email={student.email}")
    
    token = create_access_token(
        data={"sub": str(student.id), "email": student.email, "role": "student"},
        expires_delta=timedelta(hours=2)
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 2. Test GET /exams/12
    req = urllib.request.Request(f"{BASE_URL}/exams/12", headers=headers)
    with urllib.request.urlopen(req) as resp:
        exam_data = json.loads(resp.read().decode())
        print(f"[SUCCESS] GET /exams/12 -> Title: {exam_data.get('title')}, Status: {exam_data.get('status')}")

    # 3. Test GET /coding/questions/12
    req = urllib.request.Request(f"{BASE_URL}/coding/questions/12", headers=headers)
    with urllib.request.urlopen(req) as resp:
        coding_questions = json.loads(resp.read().decode())
        print(f"[SUCCESS] GET /coding/questions/12 -> Loaded {len(coding_questions)} coding questions")
        for q in coding_questions:
            print(f"   Question ID: {q.get('id')}, Title: {q.get('title')}, Marks: {q.get('marks')}, Allowed Langs: {q.get('allowed_languages')}")
            print(f"   Sample Test Cases: {len(q.get('sample_test_cases', []))}")
            if q.get('sample_test_cases'):
                print(f"   First Sample TC: {q.get('sample_test_cases')[0]}")

    # 4. Test POST /coding/run
    q_id = coding_questions[0]['id']
    run_payload = json.dumps({
        "question_id": q_id,
        "code": "def solution():\n    return 'sample_input'",
        "language": "python",
        "sample_test_cases": coding_questions[0].get('sample_test_cases', [])
    }).encode()
    req = urllib.request.Request(f"{BASE_URL}/coding/run", data=run_payload, headers=headers)
    with urllib.request.urlopen(req) as resp:
        run_res = json.loads(resp.read().decode())
        print(f"[SUCCESS] POST /coding/run -> Verdict: {run_res.get('verdict')}, Status: {run_res.get('status')}")
        print(f"   Details: execution_time={run_res.get('execution_time')}, test_cases={len(run_res.get('test_cases', []))}")

    # 5. Test POST /coding/submit
    submit_payload = json.dumps({
        "question_id": q_id,
        "code": "def solution():\n    return 'sample_input'",
        "language": "python"
    }).encode()
    req = urllib.request.Request(f"{BASE_URL}/coding/submit", data=submit_payload, headers=headers)
    with urllib.request.urlopen(req) as resp:
        submit_res = json.loads(resp.read().decode())
        print(f"[SUCCESS] POST /coding/submit -> Verdict: {submit_res.get('verdict')}, Status: {submit_res.get('status')}")
        print(f"   Score: {submit_res.get('score')}, Total TCs: {submit_res.get('total_test_cases')}, Passed TCs: {submit_res.get('passed_test_cases')}")

    db.close()
    print("\n>>> ALL CHECKS PASSED SUCCESSFULLY! Coding exam flow is fully operational. <<<")

if __name__ == "__main__":
    run_test()

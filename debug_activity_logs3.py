"""
Debug script to find activity log 500 error.
Starts the uvicorn app in-process and tests /activity-logs endpoint.
"""
import sys
sys.path.insert(0, 'backend')

import os
os.chdir('backend')

# Set env
os.environ.setdefault('DATABASE_URL', 'postgresql://postgres:sanket@localhost:5432/exam_portal_db')

# Import FastAPI app
import traceback
from sqlalchemy.orm import Session

# Load all models
from app.models import user as user_model
from app.models import activity as activity_model
from app.models import role as role_model
from app.models import exam as exam_model
from app.models import question as question_model
from app.models import attempt as attempt_model
from app.models import result as result_model
from app.models import log as log_model
from app.models import security as security_model
from app.models import notification as notification_model

from app.db.session import SessionLocal
from app.models.user import User
from app.models.log import ActivityLog
from app.schemas.activity_log import ActivityLogResponse, PaginatedActivityLogResponse
from app.services.activity_log_service import get_activity_logs

db = SessionLocal()
try:
    # Get admin user
    admin = db.query(User).filter(User.email == 'admin@examportal.com').first()
    print("Admin:", admin.email, "roles:", [r.name for r in admin.roles])
    
    # Try to call get_activity_logs
    result = get_activity_logs(db=db, current_user=admin, page=1, page_size=20)
    print("Service result keys:", list(result.keys()))
    print("Total logs:", result.get("total"))
    
    # Try to validate the response schema
    try:
        paginated = PaginatedActivityLogResponse(
            items=[ActivityLogResponse.model_validate(item) for item in result.get("items", [])],
            total=result.get("total", 0),
            page=result.get("page", 1),
            page_size=result.get("page_size", 20),
            total_pages=result.get("total_pages", 0),
        )
        print("Schema validation SUCCESS:", len(paginated.items), "items")
    except Exception as e:
        print("Schema validation FAILED:", e)
        traceback.print_exc()
        
        # Debug individual items
        for item in result.get("items", []):
            try:
                ActivityLogResponse.model_validate(item)
            except Exception as item_err:
                print(f"Item {item.id} FAILED: {item_err}")
                print(f"  columns: { {c.key: getattr(item, c.key, None) for c in item.__table__.columns} }")
            
except Exception as e:
    traceback.print_exc()
finally:
    db.close()

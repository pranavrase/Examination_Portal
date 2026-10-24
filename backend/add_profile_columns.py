"""
Migration script to add profile columns to users table
Run this script to add phone, roll_number, and college columns to the users table
"""
import sqlite3
import sys
from pathlib import Path

# Add the parent directory to the path to import app modules
sys.path.insert(0, str(Path(__file__).parent))

def migrate_database():
    db_path = Path(__file__).parent / "examportal.db"
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        columns_to_add = {
            'phone': 'VARCHAR(20)',
            'roll_number': 'VARCHAR(50)', 
            'college': 'VARCHAR(255)'
        }
        
        for column_name, column_type in columns_to_add.items():
            if column_name not in columns:
                print(f"Adding column {column_name} to users table...")
                cursor.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")
                print(f"Successfully added {column_name}")
            else:
                print(f"Column {column_name} already exists, skipping...")
        
        conn.commit()
        conn.close()
        print("Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"Migration failed: {e}")
        return False

if __name__ == "__main__":
    if migrate_database():
        print("Database migration completed successfully")
        sys.exit(0)
    else:
        print("Database migration failed")
        sys.exit(1)
import os
import sys
import psycopg2
from getpass import getpass

def main():
    print("=" * 60)
    print("PostgreSQL Database Initialization Helper for exam_portal_db")
    print("=" * 60)

    host = input("PostgreSQL Host [localhost]: ").strip() or "localhost"
    port = input("PostgreSQL Port [5432]: ").strip() or "5432"
    user = input("PostgreSQL Username [postgres]: ").strip() or "postgres"
    password = getpass("PostgreSQL Password: ").strip()

    print(f"\nConnecting to PostgreSQL server at {host}:{port} as user '{user}'...")
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname="postgres",
            connect_timeout=5
        )
        conn.autocommit = True
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'exam_portal_db';")
        exists = cursor.fetchone()

        if not exists:
            print("Creating database 'exam_portal_db'...")
            cursor.execute("CREATE DATABASE exam_portal_db;")
            print("SUCCESS: Database 'exam_portal_db' created successfully!")
        else:
            print("INFO: Database 'exam_portal_db' already exists!")

        cursor.close()
        conn.close()

        # Update .env file
        db_url = f"postgresql://{user}:{password}@{host}:{port}/exam_portal_db"
        env_path = os.path.join(os.path.dirname(__file__), ".env")

        env_content = f"""JWT_SECRET_KEY=change-this-secret-to-a-secure-random-string-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
RESET_TOKEN_EXPIRE_MINUTES=15
DATABASE_URL={db_url}
"""
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(env_content)

        print(f"Updated backend/.env with DATABASE_URL={db_url}")
        print("\nAll database setup steps completed successfully!")

    except Exception as e:
        print(f"\nERROR: Could not connect to PostgreSQL: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

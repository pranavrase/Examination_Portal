import psycopg2

passwords = ['postgres', 'admin', 'root', '1234', '123456', 'password', '', 'rishi', 'shubham']

for pwd in passwords:
    try:
        conn = psycopg2.connect(host='localhost', port=5432, user='postgres', password=pwd, dbname='postgres', connect_timeout=3)
        print(f"SUCCESS: Connected to PostgreSQL with password: '{pwd}'")
        
        # Check if exam_portal_db exists
        conn.autocommit = True
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'exam_portal_db'")
        exists = cursor.fetchone()
        if not exists:
            print("Database 'exam_portal_db' does not exist. Creating it now...")
            cursor.execute("CREATE DATABASE exam_portal_db;")
            print("Database 'exam_portal_db' created successfully!")
        else:
            print("Database 'exam_portal_db' already exists.")
        
        cursor.close()
        conn.close()
        break
    except Exception as e:
        print(f"Failed with password '{pwd}': {e}")

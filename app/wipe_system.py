import sqlite3
import os

def reset_project():
    # 1. Path to your database
    db_file = 'users.db'
    
    if os.path.exists(db_file):
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # 2. Drop the tables completely
        print("Dropping tables...")
        cursor.execute("DROP TABLE IF EXISTS users")
        cursor.execute("DROP TABLE IF EXISTS history")
        
        conn.commit()
        conn.close()
        
        # 3. Delete the file to be 100% sure
        os.remove(db_file)
        print("✅ Success: All users and history deleted permanently.")
    else:
        print("❌ Database file not found. Nothing to delete.")

if __name__ == "__main__":
    reset_project()
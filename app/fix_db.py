import sqlite3

def update_database():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # Adding new columns to the existing users table
    columns_to_add = [
        ("name", "TEXT"),
        ("gender", "TEXT"),
        ("otp", "TEXT"),
        ("is_verified", "INTEGER DEFAULT 0")
    ]
    
    for col_name, col_type in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            print(f"Added column: {col_name}")
        except sqlite3.OperationalError:
            print(f"Column {col_name} already exists.")
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    update_database()
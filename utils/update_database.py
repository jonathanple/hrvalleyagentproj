import sqlite3

def add_conversation_id_column():
    # Connect to the database
    conn = sqlite3.connect("data/conversation_database.db")
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(conversations)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if "conversation_id" not in columns:
            print("Adding conversation_id column to conversations table...")
            # Add the new column
            cursor.execute("ALTER TABLE conversations ADD COLUMN conversation_id TEXT")
            print("Column added successfully!")
        else:
            print("Column 'conversation_id' already exists.")
        
        # Initialize existing rows with a default conversation_id based on employee_id and date_time
        cursor.execute("""
        UPDATE conversations 
        SET conversation_id = employee_id || '_' || substr(date_time, 1, 10)
        WHERE conversation_id IS NULL
        """)
        print("Updated existing rows with default conversation IDs.")
        
        # Commit the changes
        conn.commit()
        print("Database updated successfully!")
    
    except Exception as e:
        print(f"Error updating database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_conversation_id_column()
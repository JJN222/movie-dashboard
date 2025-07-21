# check_db.py
# Simple database checker

import sqlite3
import os

def check_database():
    db_path = "movie_trends.db"
    
    print("🔍 Checking database...")
    
    # Check if file exists
    if not os.path.exists(db_path):
        print("❌ Database file doesn't exist!")
        return
    
    print(f"✅ Database file exists: {os.path.getsize(db_path)} bytes")
    
    # Connect and check tables
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"📋 Tables found: {tables}")
    
    # Check data in popularity_snapshots
    cursor.execute("SELECT COUNT(*) FROM popularity_snapshots")
    count = cursor.fetchone()[0]
    print(f"📊 Snapshots stored: {count}")
    
    if count > 0:
        cursor.execute("SELECT title, popularity, snapshot_date FROM popularity_snapshots LIMIT 5")
        samples = cursor.fetchall()
        print(f"📝 Sample data:")
        for title, pop, date in samples:
            print(f"   - {title}: {pop} on {date}")
    
    conn.close()

if __name__ == "__main__":
    check_database()
# simulate_trends.py
# Add some fake historical data to see trends immediately!

import sqlite3
from datetime import datetime, timedelta
import random

def simulate_historical_data():
    """Add fake historical data to see trends"""
    print("🎭 Adding simulated historical data...")
    
    conn = sqlite3.connect("movie_trends.db")
    cursor = conn.cursor()
    
    # Get current data
    cursor.execute("SELECT DISTINCT content_id, title, media_type FROM popularity_snapshots")
    current_items = cursor.fetchall()
    
    if not current_items:
        print("❌ No current data found. Run trend_detector.py first!")
        return
    
    print(f"📊 Found {len(current_items)} items to create history for...")
    
    # Add fake data for the past 5 days
    for days_ago in range(5, 0, -1):
        fake_date = (datetime.now() - timedelta(days=days_ago)).date()
        fake_time = datetime.now() - timedelta(days=days_ago)
        
        print(f"📅 Adding data for {fake_date}")
        
        for rank, (content_id, title, media_type) in enumerate(current_items[:15], 1):
            # Simulate popularity changes
            base_popularity = random.uniform(50, 200)
            
            # Some items trending up, some down
            if rank <= 5:  # Top items trending up
                trend_factor = 1 + (5 - days_ago) * 0.15  # Rising trend
            elif rank > 10:  # Lower items trending down
                trend_factor = 1 - (5 - days_ago) * 0.1   # Declining trend
            else:  # Middle items stable
                trend_factor = 1 + random.uniform(-0.05, 0.05)  # Stable
            
            fake_popularity = base_popularity * trend_factor
            fake_rating = random.uniform(6.0, 9.0)
            fake_votes = random.randint(100, 5000)
            
            cursor.execute('''
                INSERT INTO popularity_snapshots 
                (content_id, title, media_type, popularity, vote_average, vote_count, 
                 release_date, snapshot_date, snapshot_time, rank_position)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (content_id, title, media_type, fake_popularity, fake_rating, 
                  fake_votes, "2024-01-01", fake_date, fake_time, rank))
    
    conn.commit()
    conn.close()
    print("✅ Historical data added!")
    print("🚀 Now run trend_detector.py to see trends!")

if __name__ == "__main__":
    simulate_historical_data()
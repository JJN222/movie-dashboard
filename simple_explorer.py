# simple_explorer.py
# Simpler database explorer without pandas

import sqlite3
from datetime import datetime, timedelta

def show_database_overview():
    """Show basic database info"""
    conn = sqlite3.connect("movie_trends.db")
    cursor = conn.cursor()
    
    try:
        # Count snapshots
        cursor.execute("SELECT COUNT(*) FROM popularity_snapshots")
        total = cursor.fetchone()[0]
        
        # Count unique items
        cursor.execute("SELECT COUNT(DISTINCT content_id) FROM popularity_snapshots")
        unique = cursor.fetchone()[0]
        
        # Get recent data
        cursor.execute("""
            SELECT title, media_type, popularity, snapshot_date 
            FROM popularity_snapshots 
            ORDER BY snapshot_date DESC 
            LIMIT 10
        """)
        recent = cursor.fetchall()
        
        print("🗄️  DATABASE OVERVIEW")
        print("=" * 50)
        print(f"📊 Total snapshots: {total}")
        print(f"🎭 Unique items: {unique}")
        
        if recent:
            print(f"\n🕐 Recent entries:")
            for title, media_type, pop, date in recent:
                emoji = "🎬" if media_type == "movie" else "📺"
                print(f"   {emoji} {title[:30]}: {pop:.1f} on {date}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    conn.close()

def search_content(search_term):
    """Search for content"""
    conn = sqlite3.connect("movie_trends.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT title, media_type, COUNT(*) as snapshots,
               AVG(popularity) as avg_pop
        FROM popularity_snapshots 
        WHERE title LIKE ?
        GROUP BY content_id, title, media_type
        ORDER BY avg_pop DESC
    """, (f"%{search_term}%",))
    
    results = cursor.fetchall()
    
    if results:
        print(f"\n🔍 Results for '{search_term}':")
        for title, media_type, snapshots, avg_pop in results:
            emoji = "🎬" if media_type == "movie" else "📺"
            print(f"   {emoji} {title}: {avg_pop:.1f} avg ({snapshots} snapshots)")
    else:
        print(f"❌ No results for '{search_term}'")
    
    conn.close()

def main():
    print("🔍 Simple Database Explorer")
    print("=" * 30)
    
    show_database_overview()
    
    print(f"\nCommands: search <title>, overview, quit")
    
    while True:
        try:
            command = input(f"\n> ").strip()
            
            if command in ["quit", "exit"]:
                break
            elif command == "overview":
                show_database_overview()
            elif command.startswith("search "):
                search_term = command[7:]
                search_content(search_term)
            else:
                print("❓ Try: search <title>, overview, or quit")
                
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    main()
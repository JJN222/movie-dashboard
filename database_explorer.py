# database_explorer.py
# Explore and analyze your trend database!

import sqlite3
import json
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import pandas as pd

class DatabaseExplorer:
    def __init__(self, db_path="movie_trends.db"):
        self.db_path = db_path
    
    def get_database_stats(self):
        """Get basic stats about your database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Count total snapshots
        cursor.execute("SELECT COUNT(*) FROM popularity_snapshots")
        total_snapshots = cursor.fetchone()[0]
        
        # Count unique content items
        cursor.execute("SELECT COUNT(DISTINCT content_id) FROM popularity_snapshots")
        unique_items = cursor.fetchone()[0]
        
        # Get date range
        cursor.execute("SELECT MIN(snapshot_date), MAX(snapshot_date) FROM popularity_snapshots")
        date_range = cursor.fetchone()
        
        # Count by media type
        cursor.execute("""
            SELECT media_type, COUNT(DISTINCT content_id) as count 
            FROM popularity_snapshots 
            GROUP BY media_type
        """)
        media_breakdown = cursor.fetchall()
        
        conn.close()
        
        return {
            'total_snapshots': total_snapshots,
            'unique_items': unique_items,
            'date_range': date_range,
            'media_breakdown': media_breakdown
        }
    
    def get_item_history(self, content_id=None, title=None, limit=10):
        """Get popularity history for specific items"""
        conn = sqlite3.connect(self.db_path)
        
        if content_id:
            query = """
                SELECT title, media_type, popularity, snapshot_date, rank_position
                FROM popularity_snapshots 
                WHERE content_id = ?
                ORDER BY snapshot_date
            """
            df = pd.read_sql_query(query, conn, params=(content_id,))
        elif title:
            query = """
                SELECT title, media_type, popularity, snapshot_date, rank_position
                FROM popularity_snapshots 
                WHERE title LIKE ?
                ORDER BY snapshot_date
            """
            df = pd.read_sql_query(query, conn, params=(f"%{title}%",))
        else:
            # Get top trending items over time
            query = """
                SELECT title, media_type, popularity, snapshot_date, rank_position
                FROM popularity_snapshots 
                WHERE rank_position <= ?
                ORDER BY snapshot_date DESC, rank_position
                LIMIT 100
            """
            df = pd.read_sql_query(query, conn, params=(limit,))
        
        conn.close()
        return df
    
    def get_trending_over_time(self, days_back=7):
        """Get trending patterns over time"""
        conn = sqlite3.connect(self.db_path)
        
        cutoff_date = (datetime.now() - timedelta(days=days_back)).date()
        
        query = """
            SELECT title, media_type, popularity, snapshot_date, rank_position
            FROM popularity_snapshots 
            WHERE snapshot_date >= ?
            ORDER BY snapshot_date, rank_position
        """
        
        df = pd.read_sql_query(query, conn, params=(cutoff_date,))
        conn.close()
        
        return df
    
    def find_biggest_movers(self, days_back=7):
        """Find content with biggest popularity changes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days_back)).date()
        
        query = """
        WITH first_last AS (
            SELECT 
                content_id,
                title,
                media_type,
                MIN(snapshot_date) as first_date,
                MAX(snapshot_date) as last_date
            FROM popularity_snapshots 
            WHERE snapshot_date >= ?
            GROUP BY content_id, title, media_type
            HAVING COUNT(*) >= 2
        ),
        popularity_changes AS (
            SELECT 
                fl.content_id,
                fl.title,
                fl.media_type,
                first_snap.popularity as first_popularity,
                last_snap.popularity as last_popularity,
                CASE 
                    WHEN first_snap.popularity > 0 
                    THEN ((last_snap.popularity - first_snap.popularity) / first_snap.popularity) * 100
                    ELSE 0
                END as change_percent
            FROM first_last fl
            JOIN popularity_snapshots first_snap ON 
                fl.content_id = first_snap.content_id AND 
                fl.first_date = first_snap.snapshot_date
            JOIN popularity_snapshots last_snap ON 
                fl.content_id = last_snap.content_id AND 
                fl.last_date = last_snap.snapshot_date
        )
        SELECT * FROM popularity_changes 
        WHERE ABS(change_percent) > 10
        ORDER BY ABS(change_percent) DESC
        LIMIT 20
        """
        
        cursor.execute(query, (cutoff_date,))
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def display_database_overview(self):
        """Display a nice overview of your database"""
        stats = self.get_database_stats()
        
        print("🗄️  DATABASE OVERVIEW")
        print("=" * 50)
        print(f"📊 Total snapshots stored: {stats['total_snapshots']}")
        print(f"🎭 Unique content items: {stats['unique_items']}")
        
        if stats['date_range'][0]:
            print(f"📅 Data range: {stats['date_range'][0]} to {stats['date_range'][1]}")
        
        print(f"\n📺 Content breakdown:")
        for media_type, count in stats['media_breakdown']:
            emoji = "🎬" if media_type == "movie" else "📺" if media_type == "tv" else "👤"
            print(f"   {emoji} {media_type.title()}: {count} items")
    
    def display_biggest_movers(self):
        """Show the biggest popularity changes"""
        movers = self.find_biggest_movers(days_back=7)
        
        if not movers:
            print("📊 No significant changes detected yet.")
            return
        
        print(f"\n🚀 BIGGEST MOVERS (Last 7 Days)")
        print("=" * 60)
        
        for row in movers:
            content_id, title, media_type, first_pop, last_pop, change_percent = row
            
            emoji = "🎬" if media_type == "movie" else "📺"
            trend_emoji = "📈" if change_percent > 0 else "📉"
            
            print(f"{emoji} {title}")
            print(f"   {trend_emoji} {change_percent:+.1f}% ({first_pop:.1f} → {last_pop:.1f})")
            print()
    
    def search_content(self, search_term):
        """Search for specific content in your database"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
            SELECT DISTINCT title, media_type, content_id,
                   COUNT(*) as snapshots,
                   MIN(snapshot_date) as first_seen,
                   MAX(snapshot_date) as last_seen,
                   AVG(popularity) as avg_popularity
            FROM popularity_snapshots 
            WHERE title LIKE ?
            GROUP BY content_id, title, media_type
            ORDER BY avg_popularity DESC
        """
        
        cursor = conn.cursor()
        cursor.execute(query, (f"%{search_term}%",))
        results = cursor.fetchall()
        
        if results:
            print(f"\n🔍 SEARCH RESULTS for '{search_term}':")
            print("=" * 50)
            
            for row in results:
                title, media_type, content_id, snapshots, first_seen, last_seen, avg_pop = row
                emoji = "🎬" if media_type == "movie" else "📺"
                
                print(f"{emoji} {title}")
                print(f"   📊 Average popularity: {avg_pop:.1f}")
                print(f"   📅 Tracked: {first_seen} to {last_seen} ({snapshots} snapshots)")
                print(f"   🆔 ID: {content_id}")
                print()
        else:
            print(f"❌ No results found for '{search_term}'")
        
        conn.close()
        return results
    
    def export_data(self, filename=None):
        """Export all data to CSV for analysis"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"movie_trends_export_{timestamp}.csv"
        
        conn = sqlite3.connect(self.db_path)
        
        query = """
            SELECT * FROM popularity_snapshots 
            ORDER BY snapshot_date DESC, rank_position
        """
        
        df = pd.read_sql_query(query, conn)
        df.to_csv(filename, index=False)
        
        conn.close()
        print(f"💾 Data exported to {filename}")
        return filename

def main():
    print("🔍 Movie Trends Database Explorer")
    print("=" * 40)
    
    explorer = DatabaseExplorer()
    
    # Show database overview
    explorer.display_database_overview()
    
    # Show biggest movers
    explorer.display_biggest_movers()
    
    # Interactive features
    print(f"\n💡 AVAILABLE COMMANDS:")
    print("🔍 search <title>     - Search for specific content")
    print("📊 export            - Export data to CSV")
    print("📈 history <title>   - Show popularity history")
    print("❌ quit             - Exit")
    
    while True:
        try:
            command = input(f"\n> ").strip().lower()
            
            if command == "quit" or command == "exit":
                break
            elif command.startswith("search "):
                search_term = command[7:]
                explorer.search_content(search_term)
            elif command == "export":
                explorer.export_data()
            elif command.startswith("history "):
                title = command[8:]
                df = explorer.get_item_history(title=title)
                if not df.empty:
                    print(f"\n📈 POPULARITY HISTORY for '{title}':")
                    print("=" * 50)
                    for _, row in df.iterrows():
                        print(f"📅 {row['snapshot_date']}: {row['popularity']:.1f} (Rank #{row['rank_position']})")
                else:
                    print(f"❌ No history found for '{title}'")
            else:
                print("❓ Unknown command. Try: search <title>, export, history <title>, or quit")
                
        except KeyboardInterrupt:
            break
    
    print("\n👋 Thanks for exploring your trends database!")

if __name__ == "__main__":
    # Install required packages first
    try:
        import pandas as pd
        import matplotlib.pyplot as plt
        main()
    except ImportError:
        print("📦 Installing required packages...")
        import subprocess
        subprocess.check_call(["pip", "install", "pandas", "matplotlib"])
        print("✅ Packages installed! Run the script again.")
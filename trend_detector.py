# trend_detector.py
# Track popularity changes over time and detect trends!

import requests
import json
import sqlite3
from datetime import datetime, timedelta
import time
from typing import List, Dict, Optional
import statistics

# 🔑 Your API key
API_KEY = "1216ca271ce34811541580deeb170c2f"

class TrendDetector:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.themoviedb.org/3"
        self.db_path = "movie_trends.db"
        self.init_database()
    
    def init_database(self):
        """Create database tables to store historical data"""
        print("🗄️ Setting up trend tracking database...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table for storing popularity snapshots
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS popularity_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_id INTEGER,
                title TEXT,
                media_type TEXT,
                popularity REAL,
                vote_average REAL,
                vote_count INTEGER,
                release_date TEXT,
                snapshot_date DATE,
                snapshot_time DATETIME,
                rank_position INTEGER
            )
        ''')
        
        # Table for detected trends
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS detected_trends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_id INTEGER,
                title TEXT,
                media_type TEXT,
                trend_type TEXT,
                start_date DATE,
                detection_date DATE,
                start_popularity REAL,
                current_popularity REAL,
                percentage_change REAL,
                days_active INTEGER,
                status TEXT DEFAULT 'active'
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Database ready!")
    
    def get_trending_content(self, content_type="all", time_window="day"):
        """Get trending content from TMDb"""
        url = f"{self.base_url}/trending/{content_type}/{time_window}"
        params = {'api_key': self.api_key}
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response.json()['results']
            else:
                print(f"❌ API Error: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Error: {e}")
            return []
    
    def store_snapshot(self, content_list):
        """Store current popularity snapshot in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        snapshot_date = datetime.now().date()
        snapshot_time = datetime.now()
        
        print(f"💾 Storing snapshot of {len(content_list)} items...")
        
        for rank, item in enumerate(content_list, 1):
            content_id = item.get('id')
            title = item.get('title') or item.get('name', 'Unknown')
            media_type = item.get('media_type', 'unknown')
            popularity = item.get('popularity', 0)
            vote_average = item.get('vote_average', 0)
            vote_count = item.get('vote_count', 0)
            release_date = item.get('release_date') or item.get('first_air_date', '')
            
            cursor.execute('''
                INSERT INTO popularity_snapshots 
                (content_id, title, media_type, popularity, vote_average, vote_count, 
                 release_date, snapshot_date, snapshot_time, rank_position)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (content_id, title, media_type, popularity, vote_average, 
                  vote_count, release_date, snapshot_date, snapshot_time, rank))
        
        conn.commit()
        conn.close()
        print("✅ Snapshot stored!")
    
    def detect_trends(self, days_back=7, min_change_percent=20):
        """Detect trending patterns in the stored data"""
        print(f"🔍 Analyzing trends over the last {days_back} days...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get data from the last week
        cutoff_date = (datetime.now() - timedelta(days=days_back)).date()
        
        query = '''
            SELECT content_id, title, media_type, popularity, snapshot_date
            FROM popularity_snapshots 
            WHERE snapshot_date >= ?
            ORDER BY content_id, snapshot_date
        '''
        
        cursor.execute(query, (cutoff_date,))
        results = cursor.fetchall()
        
        # Group by content
        content_data = {}
        for row in results:
            content_id, title, media_type, popularity, snapshot_date = row
            
            if content_id not in content_data:
                content_data[content_id] = {
                    'title': title,
                    'media_type': media_type,
                    'snapshots': []
                }
            
            content_data[content_id]['snapshots'].append({
                'date': snapshot_date,
                'popularity': popularity
            })
        
        # Analyze trends
        detected_trends = []
        
        for content_id, data in content_data.items():
            snapshots = data['snapshots']
            
            if len(snapshots) >= 2:  # Need at least 2 data points
                # Sort by date
                snapshots.sort(key=lambda x: x['date'])
                
                first_popularity = snapshots[0]['popularity']
                last_popularity = snapshots[-1]['popularity']
                
                # Calculate percentage change
                if first_popularity > 0:
                    change_percent = ((last_popularity - first_popularity) / first_popularity) * 100
                else:
                    change_percent = 100 if last_popularity > 0 else 0
                
                # Determine trend type
                if abs(change_percent) >= min_change_percent:
                    if change_percent > 0:
                        trend_type = "Rising" if change_percent < 50 else "Surging"
                    else:
                        trend_type = "Declining" if change_percent > -50 else "Crashing"
                    
                    trend_info = {
                        'content_id': content_id,
                        'title': data['title'],
                        'media_type': data['media_type'],
                        'trend_type': trend_type,
                        'change_percent': change_percent,
                        'start_popularity': first_popularity,
                        'current_popularity': last_popularity,
                        'days_tracked': len(snapshots),
                        'snapshots': snapshots
                    }
                    
                    detected_trends.append(trend_info)
        
        conn.close()
        
        # Sort by biggest changes
        detected_trends.sort(key=lambda x: abs(x['change_percent']), reverse=True)
        
        return detected_trends
    
    def display_trends(self, trends):
        """Display detected trends in a nice format"""
        if not trends:
            print("📊 No significant trends detected yet.")
            print("💡 Try running the tracker a few times over several days to see trends!")
            return
        
        print(f"\n🔥 DETECTED TRENDS (Last 7 Days)")
        print("=" * 70)
        
        for trend in trends[:15]:  # Show top 15
            emoji = "🎬" if trend['media_type'] == "movie" else "📺"
            
            # Choose trend emoji
            if "Rising" in trend['trend_type']:
                trend_emoji = "📈"
            elif "Surging" in trend['trend_type']:
                trend_emoji = "🚀"
            elif "Declining" in trend['trend_type']:
                trend_emoji = "📉"
            else:  # Crashing
                trend_emoji = "💥"
            
            print(f"{emoji} {trend['title']}")
            print(f"   {trend_emoji} {trend['trend_type']}: {trend['change_percent']:+.1f}%")
            print(f"   📊 {trend['start_popularity']:.1f} → {trend['current_popularity']:.1f}")
            print(f"   📅 Tracked for {trend['days_tracked']} snapshots")
            print()
    
    def get_trend_summary(self, trends):
        """Generate a summary of trending patterns"""
        if not trends:
            return {}
        
        rising_count = sum(1 for t in trends if "Rising" in t['trend_type'] or "Surging" in t['trend_type'])
        declining_count = len(trends) - rising_count
        
        avg_change = statistics.mean([abs(t['change_percent']) for t in trends])
        biggest_gainer = max(trends, key=lambda x: x['change_percent'])
        biggest_loser = min(trends, key=lambda x: x['change_percent'])
        
        return {
            'total_trends': len(trends),
            'rising_count': rising_count,
            'declining_count': declining_count,
            'avg_change_percent': avg_change,
            'biggest_gainer': biggest_gainer,
            'biggest_loser': biggest_loser
        }
    
    def save_trend_report(self, trends, summary):
        """Save trend analysis to JSON"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "analysis_period": "7 days",
            "summary": summary,
            "detected_trends": trends
        }
        
        filename = f"trend_analysis_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"💾 Trend analysis saved to {filename}")
        return filename

def main():
    print("📈 Movie & TV Trend Detection System")
    print("=" * 50)
    
    detector = TrendDetector(API_KEY)
    
    # Step 1: Get current trending data
    print("📡 Getting current trending data...")
    current_trends = detector.get_trending_content("all", "day")
    
    if not current_trends:
        print("😞 No data available.")
        return
    
    # Step 2: Store current snapshot
    detector.store_snapshot(current_trends)
    
    # Step 3: Analyze trends
    trends = detector.detect_trends(days_back=7, min_change_percent=15)
    
    # Step 4: Display results
    detector.display_trends(trends)
    
    # Step 5: Generate summary
    summary = detector.get_trend_summary(trends)
    
    if summary:
        print(f"\n📊 TREND SUMMARY:")
        print(f"🔍 Total trends detected: {summary['total_trends']}")
        print(f"📈 Rising/Surging: {summary['rising_count']}")
        print(f"📉 Declining/Crashing: {summary['declining_count']}")
        print(f"📊 Average change: {summary['avg_change_percent']:.1f}%")
        
        if summary['biggest_gainer']['change_percent'] > 0:
            print(f"🏆 Biggest gainer: {summary['biggest_gainer']['title']} (+{summary['biggest_gainer']['change_percent']:.1f}%)")
        
        if summary['biggest_loser']['change_percent'] < 0:
            print(f"💥 Biggest decline: {summary['biggest_loser']['title']} ({summary['biggest_loser']['change_percent']:.1f}%)")
    
    # Step 6: Save report
    report_file = detector.save_trend_report(trends, summary)
    
    print(f"\n✨ Trend analysis complete!")
    print(f"📄 Report saved: {report_file}")
    print(f"\n💡 Run this script daily to build trend history!")

if __name__ == "__main__":
    main()
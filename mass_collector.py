# mass_collector.py
# Collect thousands of movies and TV shows!

import requests
import sqlite3
from datetime import datetime
import time

API_KEY = "1216ca271ce34811541580deeb170c2f"

class MassCollector:
    def __init__(self):
        self.api_key = API_KEY
        self.base_url = "https://api.themoviedb.org/3"
        self.db_path = "movie_trends.db"
    
    def collect_comprehensive_data(self):
        """Collect thousands of movies and TV shows"""
        print("🚀 Starting comprehensive data collection...")
        
        all_content = []
        
        # 1. Multiple trending time windows
        for time_window in ['day', 'week']:
            for media_type in ['movie', 'tv']:
                content = self.get_trending_content(media_type, time_window)
                all_content.extend(content)
                time.sleep(0.3)  # Rate limiting
        
        # 2. Popular content (multiple pages)
        for media_type in ['movie', 'tv']:
            for page in range(1, 11):  # Get 10 pages = 200 items each
                content = self.get_popular_content(media_type, page)
                all_content.extend(content)
                time.sleep(0.3)
                print(f"📄 Collected page {page} of {media_type}s...")
        
        # 3. Top rated content
        for media_type in ['movie', 'tv']:
            for page in range(1, 6):  # Get 5 pages = 100 items each
                content = self.get_top_rated_content(media_type, page)
                all_content.extend(content)
                time.sleep(0.3)
        
        # 4. Discover by different criteria
        discover_params = [
            {'sort_by': 'popularity.desc', 'vote_count.gte': 100},
            {'sort_by': 'vote_average.desc', 'vote_count.gte': 500},
            {'sort_by': 'revenue.desc'},
            {'sort_by': 'release_date.desc', 'vote_count.gte': 50},
        ]
        
        for params in discover_params:
            for media_type in ['movie', 'tv']:
                for page in range(1, 6):
                    content = self.discover_content(media_type, params, page)
                    all_content.extend(content)
                    time.sleep(0.3)
        
        # Remove duplicates
        unique_content = self.deduplicate_content(all_content)
        
        print(f"✅ Collected {len(unique_content)} unique items!")
        
        # Store in database
        self.store_mass_data(unique_content)
        
        return unique_content
    
    def get_trending_content(self, media_type, time_window):
        """Get trending content"""
        url = f"{self.base_url}/trending/{media_type}/{time_window}"
        params = {'api_key': self.api_key}
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response.json()['results']
        except Exception as e:
            print(f"❌ Error getting trending {media_type}: {e}")
        return []
    
    def get_popular_content(self, media_type, page=1):
        """Get popular content with pagination"""
        url = f"{self.base_url}/{media_type}/popular"
        params = {'api_key': self.api_key, 'page': page}
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response.json()['results']
        except Exception as e:
            print(f"❌ Error getting popular {media_type} page {page}: {e}")
        return []
    
    def get_top_rated_content(self, media_type, page=1):
        """Get top rated content"""
        url = f"{self.base_url}/{media_type}/top_rated"
        params = {'api_key': self.api_key, 'page': page}
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response.json()['results']
        except Exception as e:
            print(f"❌ Error getting top rated {media_type}: {e}")
        return []
    
    def discover_content(self, media_type, params, page=1):
        """Discover content with custom parameters"""
        url = f"{self.base_url}/discover/{media_type}"
        api_params = {'api_key': self.api_key, 'page': page}
        api_params.update(params)
        
        try:
            response = requests.get(url, params=api_params)
            if response.status_code == 200:
                return response.json()['results']
        except Exception as e:
            print(f"❌ Error discovering {media_type}: {e}")
        return []
    
    def deduplicate_content(self, content_list):
        """Remove duplicate content"""
        seen = set()
        unique_content = []
        
        for item in content_list:
            # Create unique key
            title = item.get('title') or item.get('name', '')
            media_type = item.get('media_type', 'unknown')
            key = (item.get('id'), title, media_type)
            
            if key not in seen:
                seen.add(key)
                unique_content.append(item)
        
        return unique_content
    
    def store_mass_data(self, content_list):
        """Store collected data in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.now()
        date_collected = timestamp.date()
        
        print(f"💾 Storing {len(content_list)} items...")
        
        for rank, item in enumerate(content_list, 1):
            content_id = item.get('id')
            title = item.get('title') or item.get('name', 'Unknown')
            media_type = item.get('media_type', 'unknown')
            popularity = item.get('popularity', 0)
            vote_average = item.get('vote_average', 0)
            vote_count = item.get('vote_count', 0)
            release_date = item.get('release_date') or item.get('first_air_date', '')
            
            cursor.execute('''
                INSERT OR REPLACE INTO popularity_snapshots 
                (content_id, title, media_type, popularity, vote_average, vote_count, 
                 release_date, snapshot_date, snapshot_time, rank_position)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (content_id, title, media_type, popularity, vote_average, 
                  vote_count, release_date, date_collected, timestamp, rank))
        
        conn.commit()
        conn.close()
        print("✅ Mass data stored!")

if __name__ == "__main__":
    collector = MassCollector()
    collector.collect_comprehensive_data()
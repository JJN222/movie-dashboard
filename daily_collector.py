# enhanced_daily_collector.py
# Collect comprehensive data with production company information

import requests
import sqlite3
from datetime import datetime
import time
import json

API_KEY = "1216ca271ce34811541580deeb170c2f"

class EnhancedDailyCollector:
    def __init__(self):
        self.api_key = API_KEY
        self.base_url = "https://api.themoviedb.org/3"
        self.db_path = "movie_trends.db"
        
    def init_database_with_companies(self):
        """Update database schema to include production companies"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Add production_companies column if it doesn't exist
            cursor.execute('ALTER TABLE popularity_snapshots ADD COLUMN production_companies TEXT')
            print("✅ Added production_companies column")
        except:
            print("📋 Production companies column already exists")
        
        # Create production_companies table for better organization
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS production_companies (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE,
            country TEXT,
            content_count INTEGER DEFAULT 0
        )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Database schema updated!")

    def get_detailed_content_info(self, content_id, media_type):
        """Get detailed info including production companies"""
        endpoint = f"/{media_type}/{content_id}"
        try:
            response = requests.get(
                f"{self.base_url}{endpoint}",
                params={'api_key': self.api_key}
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"❌ Error getting details for {content_id}: {e}")
        return None

    def get_external_ids(self, content_id, media_type):
        """Get IMDB ID for a movie/show"""
        endpoint = f"/{media_type}/{content_id}/external_ids"
        try:
            response = requests.get(
                f"{self.base_url}{endpoint}",
                params={'api_key': self.api_key}
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('imdb_id')
        except Exception:
            pass
        return None

    def extract_production_companies(self, details):
        """Extract production company names from detailed content info"""
        if not details:
            return []
        
        companies = []
        production_companies = details.get('production_companies', [])
        
        for company in production_companies:
            company_name = company.get('name', '')
            if company_name:
                companies.append(company_name)
        
        return companies

    def run_enhanced_daily_collection(self):
        """Run comprehensive daily data collection with production companies"""
        print("📅 Starting enhanced daily collection with production companies...")
        print("🕐 This will take longer but will include production company data...")
        
        # Initialize database schema
        self.init_database_with_companies()
        
        all_content = []
        
        # 1. Current trending (multiple time windows)
        print("📈 Getting trending content...")
        for time_window in ['day', 'week']:
            for media_type in ['movie', 'tv']:
                content = self.get_api_data(f"/trending/{media_type}/{time_window}")
                all_content.extend(content)
                time.sleep(0.3)

        # 2. Popular content (get many pages for comprehensive coverage)
        print("🔥 Getting popular content...")
        for media_type in ['movie', 'tv']:
            for page in range(1, 11):  # 10 pages = 200 items each type
                content = self.get_api_data(f"/{media_type}/popular", {'page': page})
                all_content.extend(content)
                if page % 5 == 0:
                    print(f"  📄 Collected {page * 20} {media_type}s...")
                time.sleep(0.3)

        # 3. Top rated content
        print("⭐ Getting top rated content...")
        for media_type in ['movie', 'tv']:
            for page in range(1, 6):  # 5 pages = 100 items each
                content = self.get_api_data(f"/{media_type}/top_rated", {'page': page})
                all_content.extend(content)
                time.sleep(0.3)

        # Remove duplicates
        print("🔧 Deduplicating content...")
        unique_content = self.deduplicate_content(all_content)
        print(f"✅ Collected {len(unique_content)} unique items!")

        # Store in database WITH production company info
        self.store_enhanced_data(unique_content)
        
        return len(unique_content)

    def get_api_data(self, endpoint, params=None):
        """Get data from TMDb API"""
        if params is None:
            params = {}
        params['api_key'] = self.api_key
        
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get('results', [])
            elif response.status_code == 429:  # Rate limited
                print("⏳ Rate limited, waiting 10 seconds...")
                time.sleep(10)
                return self.get_api_data(endpoint, params)
        except Exception as e:
            print(f"❌ Error getting {endpoint}: {e}")
        return []

    def deduplicate_content(self, content_list):
        """Remove duplicate content"""
        seen = set()
        unique_content = []
        
        for item in content_list:
            content_id = item.get('id')
            if content_id and content_id not in seen:
                seen.add(content_id)
                unique_content.append(item)
        
        return unique_content

    def store_enhanced_data(self, content_list):
        """Store collected data with production company information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.now()
        date_collected = timestamp.date()
        
        print(f"💾 Storing {len(content_list)} items with production company data...")
        
        stored_count = 0
        company_cache = {}  # Cache to avoid duplicate API calls
        
        for rank, item in enumerate(content_list, 1):
            content_id = item.get('id')
            title = item.get('title') or item.get('name', 'Unknown')
            media_type = item.get('media_type', 'unknown')
            
            # Set media_type if not provided
            if media_type == 'unknown':
                if 'title' in item and 'release_date' in item:
                    media_type = 'movie'
                elif 'name' in item and 'first_air_date' in item:
                    media_type = 'tv'
            
            popularity = item.get('popularity', 0)
            vote_average = item.get('vote_average', 0)
            vote_count = item.get('vote_count', 0)
            release_date = item.get('release_date') or item.get('first_air_date', '')
            
            # Get IMDB ID
            imdb_id = self.get_external_ids(content_id, media_type)
            time.sleep(0.1)
            
            # Get detailed info for production companies
            production_companies = []
            if content_id not in company_cache:
                details = self.get_detailed_content_info(content_id, media_type)
                companies = self.extract_production_companies(details)
                company_cache[content_id] = companies
                time.sleep(0.2)  # Rate limiting for detailed calls
            else:
                companies = company_cache[content_id]
            
            # Convert companies list to JSON string for storage
            companies_json = json.dumps(companies) if companies else '[]'
            
            try:
                cursor.execute('''
                INSERT OR REPLACE INTO popularity_snapshots
                (content_id, title, media_type, popularity, vote_average, vote_count,
                 release_date, snapshot_date, snapshot_time, rank_position, imdb_id, production_companies)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (content_id, title, media_type, popularity, vote_average,
                      vote_count, release_date, date_collected, timestamp, rank, imdb_id, companies_json))
                
                stored_count += 1
                
                # Store unique production companies
                for company_name in companies:
                    cursor.execute('''
                    INSERT OR IGNORE INTO production_companies (name, content_count)
                    VALUES (?, 1)
                    ''', (company_name,))
                    
                    cursor.execute('''
                    UPDATE production_companies 
                    SET content_count = content_count + 1 
                    WHERE name = ?
                    ''', (company_name,))
                
                if stored_count % 100 == 0:
                    print(f"  💾 Stored {stored_count} items...")
                    conn.commit()  # Commit periodically
                    
            except Exception as e:
                print(f"❌ Error storing {title}: {e}")
        
        conn.commit()
        conn.close()
        
        print(f"✅ Successfully stored {stored_count} items with production company data!")
        
        # Show final stats
        self.show_enhanced_database_stats()

    def show_enhanced_database_stats(self):
        """Show database statistics including production companies"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Basic stats
        cursor.execute("SELECT COUNT(*) FROM popularity_snapshots")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT content_id) FROM popularity_snapshots")
        unique_items = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT content_id) FROM popularity_snapshots WHERE media_type = 'movie'")
        movies = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT content_id) FROM popularity_snapshots WHERE media_type = 'tv'")
        tv_shows = cursor.fetchone()[0]
        
        # Production company stats
        cursor.execute("SELECT COUNT(*) FROM production_companies")
        total_companies = cursor.fetchone()[0]
        
        cursor.execute("""
        SELECT name, content_count FROM production_companies 
        ORDER BY content_count DESC 
        LIMIT 10
        """)
        top_companies = cursor.fetchall()
        
        print(f"\n📊 ENHANCED DATABASE STATS:")
        print(f"  📈 Total snapshots: {total:,}")
        print(f"  🎭 Unique items: {unique_items:,}")
        print(f"  🎬 Movies: {movies:,}")
        print(f"  📺 TV Shows: {tv_shows:,}")
        print(f"  🏭 Production Companies: {total_companies:,}")
        
        print(f"\n🏆 TOP 10 PRODUCTION COMPANIES:")
        for i, (name, count) in enumerate(top_companies, 1):
            print(f"  {i:2d}. {name}: {count} items")
        
        conn.close()

if __name__ == "__main__":
    collector = EnhancedDailyCollector()
    total_collected = collector.run_enhanced_daily_collection()
    print(f"\n🎉 Enhanced collection complete!")
    print(f"📊 Collected {total_collected:,} unique items with production company data")
    print(f"🔄 Next collection in 24 hours")
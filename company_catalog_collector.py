# company_catalog_collector.py
# Collect ALL content from specific production companies

import requests
import sqlite3
import time
import json
from datetime import datetime

API_KEY = "1216ca271ce34811541580deeb170c2f"

class CompanyCatalogCollector:
    def __init__(self):
        self.api_key = API_KEY
        self.base_url = "https://api.themoviedb.org/3"
        self.db_path = "movie_trends.db"
        
        # Major production companies with their TMDb IDs
        self.companies = {
            'Lionsgate': 1632,  # Lionsgate Entertainment
            'Disney': 2,        # Walt Disney Pictures  
            'Warner Bros.': 174, # Warner Bros. Pictures
            'Universal': 33,     # Universal Pictures
            'Paramount': 4,      # Paramount Pictures
            'Sony': 5,          # Sony Pictures
            'Netflix': 213,     # Netflix
            'HBO': 49,          # HBO
            'Apple': 2552,      # Apple Studios
            'Amazon': 1024      # Amazon Studios
        }
    
    def collect_company_catalog(self, company_name, company_id):
        """Collect ALL movies and TV shows from a specific company"""
        print(f"🏭 Collecting ALL content for {company_name}...")
        
        all_content = []
        
        # Get movies from this company
        print(f"🎬 Getting {company_name} movies...")
        movies = self.get_company_content('movie', company_id)
        all_content.extend(movies)
        
        # Get TV shows from this company  
        print(f"📺 Getting {company_name} TV shows...")
        tv_shows = self.get_company_content('tv', company_id)
        all_content.extend(tv_shows)
        
        print(f"✅ Found {len(all_content)} total items for {company_name}")
        
        # Store in database
        if all_content:
            self.store_company_content(all_content, company_name)
            
        return len(all_content)
    
    def get_company_content(self, media_type, company_id, max_pages=20):
        """Get all movies or TV shows from a company"""
        all_items = []
        
        for page in range(1, max_pages + 1):
            url = f"{self.base_url}/discover/{media_type}"
            params = {
                'api_key': self.api_key,
                'with_companies': company_id,
                'page': page,
                'sort_by': 'popularity.desc'
            }
            
            try:
                response = requests.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])
                    
                    if not results:  # No more content
                        break
                        
                    all_items.extend(results)
                    print(f"  📄 Page {page}: {len(results)} items (Total: {len(all_items)})")
                    
                    # Check if we've reached the end
                    if page >= data.get('total_pages', 1):
                        break
                        
                else:
                    print(f"  ❌ Error on page {page}: {response.status_code}")
                    break
                    
            except Exception as e:
                print(f"  ❌ Exception on page {page}: {e}")
                break
                
            time.sleep(0.3)  # Rate limiting
            
        return all_items
    
    def store_company_content(self, content_list, company_name):
        """Store company content in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.now()
        date_collected = timestamp.date()
        
        print(f"💾 Storing {len(content_list)} {company_name} items...")
        
        stored_count = 0
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
            
            # Set production companies to the company we're collecting for
            production_companies = json.dumps([company_name])
            
            try:
                cursor.execute('''
                INSERT OR REPLACE INTO popularity_snapshots
                (content_id, title, media_type, popularity, vote_average, vote_count,
                 release_date, snapshot_date, snapshot_time, rank_position, production_companies)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (content_id, title, media_type, popularity, vote_average,
                      vote_count, release_date, date_collected, timestamp, rank, production_companies))
                
                stored_count += 1
                
                if stored_count % 100 == 0:
                    print(f"  💾 Stored {stored_count} items...")
                    
            except Exception as e:
                print(f"  ❌ Error storing {title}: {e}")
        
        conn.commit()
        conn.close()
        print(f"✅ Successfully stored {stored_count} {company_name} items!")

def main():
    print("🏭 Company Catalog Collector Starting...")
    print("=" * 50)
    
    collector = CompanyCatalogCollector()
    
    # Collect for specific companies (start with Lionsgate)
    companies_to_collect = ['Lionsgate', 'Disney', 'Netflix', 'Warner Bros.']
    
    total_collected = 0
    for company_name in companies_to_collect:
        if company_name in collector.companies:
            company_id = collector.companies[company_name]
            count = collector.collect_company_catalog(company_name, company_id)
            total_collected += count
            print(f"📊 {company_name}: {count} items")
            print("-" * 30)
    
    print(f"\n🎉 Collection Complete!")
    print(f"📊 Total items collected: {total_collected}")

if __name__ == "__main__":
    main()
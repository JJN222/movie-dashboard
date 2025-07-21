# comprehensive_studio_collector.py
# Collect complete catalogs for major studios including all their divisions

import requests
import sqlite3
import json
import time
from datetime import datetime

class ComprehensiveStudioCollector:
    def __init__(self, api_key="1216ca271ce34811541580deeb170c2f", db_path="movie_trends.db"):
        self.api_key = api_key
        self.db_path = db_path
        self.base_url = "https://api.themoviedb.org/3"
        
        # Major studios with ALL their divisions and subsidiaries
        self.studio_groups = {
            'Universal': [
                33,      # Universal Pictures
                122088,  # universal studios
                160407,  # Universal Studios
                26559,   # NBCUniversal
                95155,   # NBCUniversal International Studios
                103915,  # Universal Pictures (Australasia)
                166,     # NBCUniversal (alternate)
                10146,   # Focus Features (Universal subsidiary)
            ],
            'Paramount': [
                4,       # Paramount Pictures
                96540,   # Paramount Players
                107355,  # Paramount Pictures Brasil
                21,      # Paramount Global
                95689,   # Paramount Players (alternate)
            ],
            'Sony': [
                34,      # Sony Pictures
                5,       # Columbia Pictures
                559,     # TriStar Pictures
                2251,    # Sony Pictures Animation
                128664,  # Columbia Pictures Corporation
                192007,  # TriStar Pictures Productions
                82346,   # Sony Pictures (alternate)
            ],
            'Netflix': [
                178464,  # Netflix
                198834,  # Netflix (alternate)
                185004,  # Netflix (third variation found earlier)
            ],
            'Disney': [
                2,       # Walt Disney Pictures
                3166,    # Walt Disney Animation Studios
                6125,    # Pixar Animation Studios
                7505,    # Marvel Studios
                1,       # Walt Disney Productions
                130,     # Walt Disney Company
            ],
            'Warner Bros.': [
                174,     # Warner Bros. Pictures
                12,      # New Line Cinema
                923,     # Legendary Pictures
                128064,  # DC Films
                429,     # Warner Bros. Animation
                2785,    # Warner Bros. Television
            ]
        }
    
    def collect_studio_content(self, studio_name, company_ids):
        """Collect all content for a studio from multiple company IDs"""
        print(f"\n🎬 Collecting content for {studio_name}...")
        all_content = {}
        
        for company_id in company_ids:
            print(f"  📡 Getting content from company ID {company_id}...")
            
            # Get movies for this company
            movies = self.get_company_content(company_id, 'movie')
            print(f"    🎬 Found {len(movies)} movies")
            
            # Get TV shows for this company
            tv_shows = self.get_company_content(company_id, 'tv')
            print(f"    📺 Found {len(tv_shows)} TV shows")
            
            # Combine content (avoiding duplicates by content_id)
            for content in movies + tv_shows:
                content_id = content['id']
                if content_id not in all_content:
                    all_content[content_id] = content
            
            time.sleep(0.2)  # Rate limiting
        
        print(f"  ✅ Total unique content for {studio_name}: {len(all_content)}")
        return list(all_content.values())
    
    def get_company_content(self, company_id, content_type='movie'):
        """Get all content for a specific company ID"""
        all_content = []
        page = 1
        max_pages = 10  # Limit to avoid excessive API calls
        
        while page <= max_pages:
            endpoint = f"/discover/{content_type}"
            params = {
                'api_key': self.api_key,
                'with_companies': company_id,
                'page': page,
                'sort_by': 'popularity.desc'
            }
            
            try:
                response = requests.get(f"{self.base_url}{endpoint}", params=params)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])
                    
                    if not results:
                        break
                    
                    # Add content type and company info to each item
                    for item in results:
                        item['media_type'] = content_type
                        item['studio_company_id'] = company_id
                    
                    all_content.extend(results)
                    
                    # Check if there are more pages
                    if page >= data.get('total_pages', 1):
                        break
                    
                    page += 1
                    time.sleep(0.1)  # Rate limiting
                else:
                    print(f"    ❌ Error {response.status_code} for company {company_id}, page {page}")
                    break
                    
            except Exception as e:
                print(f"    ❌ Exception for company {company_id}: {e}")
                break
        
        return all_content
    
    def get_detailed_content_info(self, content_id, media_type):
        """Get detailed information including production companies"""
        endpoint = f"/{media_type}/{content_id}"
        params = {'api_key': self.api_key}
        
        try:
            response = requests.get(f"{self.base_url}{endpoint}", params=params)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"    ❌ Error getting details for {media_type} {content_id}: {e}")
        
        return None
    
    def store_studio_content(self, studio_name, content_list):
        """Store content in database with proper production company data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stored_count = 0
        for item in content_list:
            try:
                # Get detailed info including production companies
                detailed_info = self.get_detailed_content_info(item['id'], item['media_type'])
                if not detailed_info:
                    continue
                
                # Extract production companies
                production_companies = []
                if 'production_companies' in detailed_info:
                    production_companies = [comp['name'] for comp in detailed_info['production_companies']]
                
                # Get external IDs for IMDB
                imdb_id = None
                external_response = requests.get(
                    f"{self.base_url}/{item['media_type']}/{item['id']}/external_ids",
                    params={'api_key': self.api_key}
                )
                if external_response.status_code == 200:
                    external_data = external_response.json()
                    imdb_id = external_data.get('imdb_id')
                
                # Prepare data for database
                title = item.get('title') or item.get('name', 'Unknown')
                release_date = item.get('release_date') or item.get('first_air_date', '')
                popularity = item.get('popularity', 0)
                vote_average = item.get('vote_average', 0)
                vote_count = item.get('vote_count', 0)
                
                # Insert into database
                cursor.execute('''
                    INSERT OR REPLACE INTO popularity_snapshots 
                    (content_id, title, media_type, popularity, vote_average, vote_count, 
                     release_date, snapshot_date, snapshot_time, rank_position, imdb_id, production_companies)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    item['id'],
                    title,
                    item['media_type'],
                    popularity,
                    vote_average,
                    vote_count,
                    release_date,
                    datetime.now().strftime('%Y-%m-%d'),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    0,  # rank_position
                    imdb_id,
                    json.dumps(production_companies)
                ))
                
                stored_count += 1
                
                if stored_count % 50 == 0:
                    print(f"    💾 Stored {stored_count} items for {studio_name}...")
                    conn.commit()
                
                time.sleep(0.1)  # Rate limiting
                
            except Exception as e:
                print(f"    ❌ Error storing item {item.get('title', 'Unknown')}: {e}")
                continue
        
        conn.commit()
        conn.close()
        print(f"  ✅ Stored {stored_count} items for {studio_name}")
        return stored_count
    
    def collect_all_major_studios(self):
        """Collect content for all major studio groups"""
        print("🏭 Starting Comprehensive Major Studio Collection...")
        print("=" * 60)
        
        total_collected = 0
        
        for studio_name, company_ids in self.studio_groups.items():
            print(f"\n🎯 Processing {studio_name} ({len(company_ids)} company divisions)")
            
            # Collect content from all divisions
            content = self.collect_studio_content(studio_name, company_ids)
            
            # Store in database
            stored = self.store_studio_content(studio_name, content)
            total_collected += stored
            
            print(f"  🏆 {studio_name} complete: {stored} items added to database")
        
        print(f"\n🎉 Collection Complete!")
        print(f"📊 Total items collected: {total_collected}")
        
        # Show final studio counts
        self.show_final_studio_counts()
    
    def show_final_studio_counts(self):
        """Show final counts for each major studio"""
        print(f"\n📈 FINAL MAJOR STUDIO COUNTS:")
        print("=" * 40)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        studios = ['Universal', 'Paramount', 'Sony', 'Netflix', 'Disney', 'Warner Bros.']
        
        for studio in studios:
            cursor.execute("""
                SELECT COUNT(DISTINCT title) FROM popularity_snapshots
                WHERE production_companies LIKE ?
            """, (f"%{studio}%",))
            count = cursor.fetchone()[0]
            print(f"  🏭 {studio}: {count:,} items")
        
        conn.close()

def main():
    collector = ComprehensiveStudioCollector()
    collector.collect_all_major_studios()

if __name__ == "__main__":
    main()
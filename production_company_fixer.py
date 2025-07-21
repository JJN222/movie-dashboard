# production_company_fixer.py
# Fix missing production company data for existing items

import requests
import sqlite3
import json
import time
from datetime import datetime

API_KEY = "1216ca271ce34811541580deeb170c2f"

class ProductionCompanyFixer:
    def __init__(self):
        self.api_key = API_KEY
        self.base_url = "https://api.themoviedb.org/3"
        self.db_path = "movie_trends.db"
    
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
            elif response.status_code == 429:
                print("⏳ Rate limited, waiting 10 seconds...")
                time.sleep(10)
                return self.get_detailed_content_info(content_id, media_type)
        except Exception as e:
            print(f"❌ Error getting details for {content_id}: {e}")
        return None

    def extract_production_companies(self, details):
        """Extract ALL production company names from detailed content info"""
        if not details:
            return []
        
        companies = []
        
        # Get production companies
        production_companies = details.get('production_companies', [])
        for company in production_companies:
            company_name = company.get('name', '').strip()
            if company_name and company_name not in companies:
                companies.append(company_name)
        
        # For TV shows, also check networks
        if 'networks' in details:
            networks = details.get('networks', [])
            for network in networks:
                network_name = network.get('name', '').strip()
                if network_name and network_name not in companies:
                    companies.append(network_name)
        
        return companies

    def fix_missing_production_companies(self):
        """Fix items that are missing production company data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Find items with missing or empty production companies
        query = """
        SELECT DISTINCT content_id, title, media_type 
        FROM popularity_snapshots
        WHERE (production_companies IS NULL OR production_companies = '[]')
        AND snapshot_date = (SELECT MAX(snapshot_date) FROM popularity_snapshots)
        AND media_type IN ('movie', 'tv')
        ORDER BY popularity DESC
        LIMIT 500
        """
        
        cursor.execute(query)
        missing_items = cursor.fetchall()
        
        print(f"🔧 Found {len(missing_items)} items missing production company data")
        print("🕐 This will take about 10-15 minutes...")
        
        fixed_count = 0
        company_cache = {}
        
        for i, (content_id, title, media_type) in enumerate(missing_items, 1):
            print(f"📊 Processing {i}/{len(missing_items)}: {title[:50]}...")
            
            # Get detailed info
            if content_id not in company_cache:
                details = self.get_detailed_content_info(content_id, media_type)
                companies = self.extract_production_companies(details)
                company_cache[content_id] = companies
                time.sleep(0.25)  # Rate limiting
            else:
                companies = company_cache[content_id]
            
            # Update database with production companies
            if companies:
                companies_json = json.dumps(companies)
                
                cursor.execute("""
                UPDATE popularity_snapshots 
                SET production_companies = ?
                WHERE content_id = ? AND media_type = ?
                """, (companies_json, content_id, media_type))
                
                # Update production_companies table
                for company_name in companies:
                    cursor.execute("""
                    INSERT OR IGNORE INTO production_companies (name, content_count)
                    VALUES (?, 0)
                    """, (company_name,))
                    
                    cursor.execute("""
                    UPDATE production_companies 
                    SET content_count = content_count + 1 
                    WHERE name = ?
                    """, (company_name,))
                
                fixed_count += 1
                print(f"  ✅ Added companies: {', '.join(companies[:3])}{'...' if len(companies) > 3 else ''}")
            else:
                print(f"  ❌ No companies found")
            
            # Commit every 20 items
            if i % 20 == 0:
                conn.commit()
                print(f"  💾 Saved progress ({fixed_count} items fixed so far)")
        
        conn.commit()
        conn.close()
        
        print(f"\n✅ Fixed {fixed_count} items with production company data!")
        self.show_updated_stats()

    def normalize_company_names(self):
        """Normalize similar company names"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        print("🔧 Normalizing company names...")
        
        # Define company name mappings
        company_mappings = {
            # Netflix variations
            'Netflix': ['Netflix', 'Netflix Studios', 'Netflix International Pictures', 'Netflix Original'],
            'Lionsgate': ['Lionsgate', 'Lions Gate Entertainment', 'Lions Gate Films', 'Lionsgate Films'],
            'Disney': ['Walt Disney Pictures', 'Disney', 'The Walt Disney Company', 'Walt Disney Studios Motion Pictures'],
            'Warner Bros.': ['Warner Bros. Pictures', 'Warner Bros.', 'Warner Brothers', 'Warner Bros. Entertainment'],
            'Universal': ['Universal Pictures', 'Universal Studios', 'Universal', 'NBC Universal'],
            'Paramount': ['Paramount Pictures', 'Paramount', 'Paramount Pictures Corporation'],
            'Sony': ['Sony Pictures', 'Sony Pictures Entertainment', 'Columbia Pictures', 'Sony'],
            'Apple': ['Apple TV+', 'Apple Studios', 'Apple Original Films'],
            'Amazon': ['Amazon Studios', 'Amazon Prime Video', 'Prime Video'],
            'HBO': ['HBO', 'HBO Max', 'HBO Films', 'HBO Entertainment'],
            'Hulu': ['Hulu', 'Hulu Originals'],
            'Fox': ['20th Century Fox', '20th Century Studios', 'Fox', 'Fox Entertainment']
        }
        
        # Get all current production companies
        cursor.execute("SELECT name, content_count FROM production_companies")
        current_companies = cursor.fetchall()
        
        # Group similar companies
        normalized_companies = {}
        for company_name, count in current_companies:
            # Find which group this company belongs to
            found_group = None
            for main_name, variations in company_mappings.items():
                if any(variation.lower() in company_name.lower() or company_name.lower() in variation.lower() 
                       for variation in variations):
                    found_group = main_name
                    break
            
            if found_group:
                if found_group not in normalized_companies:
                    normalized_companies[found_group] = []
                normalized_companies[found_group].append((company_name, count))
            else:
                # Keep as-is if no group found
                normalized_companies[company_name] = [(company_name, count)]
        
        print(f"\n🏭 NORMALIZED PRODUCTION COMPANIES:")
        for main_name, variations in normalized_companies.items():
            total_count = sum(count for _, count in variations)
            if total_count >= 5:  # Only show companies with 5+ items
                print(f"  {main_name}: {total_count} items")
                if len(variations) > 1:
                    print(f"    (includes: {', '.join([name for name, _ in variations])})")
        
        conn.close()

    def show_updated_stats(self):
        """Show updated database statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Updated company stats
        cursor.execute("""
        SELECT name, content_count FROM production_companies 
        WHERE content_count >= 3
        ORDER BY content_count DESC 
        LIMIT 20
        """)
        top_companies = cursor.fetchall()
        
        print(f"\n🏆 TOP 20 PRODUCTION COMPANIES (Updated):")
        for i, (name, count) in enumerate(top_companies, 1):
            print(f"  {i:2d}. {name}: {count} items")
        
        # Coverage stats
        cursor.execute("""
        SELECT COUNT(*) FROM popularity_snapshots 
        WHERE production_companies IS NOT NULL AND production_companies != '[]'
        AND snapshot_date = (SELECT MAX(snapshot_date) FROM popularity_snapshots)
        """)
        with_companies = cursor.fetchone()[0]
        
        cursor.execute("""
        SELECT COUNT(*) FROM popularity_snapshots 
        WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM popularity_snapshots)
        """)
        total_items = cursor.fetchone()[0]
        
        coverage = (with_companies / total_items) * 100
        print(f"\n📊 PRODUCTION COMPANY COVERAGE:")
        print(f"  Items with companies: {with_companies}/{total_items} ({coverage:.1f}%)")
        
        conn.close()

if __name__ == "__main__":
    fixer = ProductionCompanyFixer()
    
    print("🔧 Starting Production Company Data Fix...")
    print("This will:")
    print("  1. Find items missing production company data")
    print("  2. Fetch detailed info from TMDb API")
    print("  3. Update your database with complete company info")
    print("  4. Show normalized company statistics")
    
    fixer.fix_missing_production_companies()
    fixer.normalize_company_names()
    
    print("\n🎉 Production company data fix complete!")
    print("🚀 Now restart your web app to see all the companies!")
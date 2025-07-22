# web_app.py
# Simplified web interface - no pandas/plotly dependencies

from flask import Flask, render_template, jsonify, request
import sqlite3
import json
import os
from datetime import datetime, timedelta

app = Flask(__name__)

class WebTrendAnalyzer:
    def __init__(self, db_path="movie_trends.db"):
        self.db_path = db_path
    
    def get_dashboard_data(self, company_filters=None):
        """Get all data needed for the dashboard with optional company filters"""
        conn = sqlite3.connect(self.db_path)
        
        # Get basic stats
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM popularity_snapshots")
        total_snapshots = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT content_id) FROM popularity_snapshots")
        unique_items = cursor.fetchone()[0]
        
        try:
            # Handle company filters safely
            has_company_filter = (company_filters and 
                                isinstance(company_filters, list) and 
                                len(company_filters) > 0 and 
                                company_filters != ['all'] and
                                company_filters[0] != 'all')
            
            if has_company_filter:
                # Company filtering logic
                where_conditions = [
                    "media_type IN ('movie', 'tv')",
                    "popularity > 5",
                    "title NOT LIKE '%Lee Chae-dam%'",
                    "title NOT LIKE '%Nukitashi%'"
                ]
                
                company_conditions = []
                for company in company_filters:
                    if company and company != 'all':
                        safe_company = company.replace("'", "''")
                        company_conditions.append(f"production_companies LIKE '%{safe_company}%'")
                
                if company_conditions:
                    where_conditions.append(f"({' OR '.join(company_conditions)})")
                
                where_clause = " AND ".join(where_conditions)
                limit_clause = "LIMIT 500"
                
            else:
                # NO COMPANY FILTER - LOOK AT LAST 2 DAYS FOR COMPREHENSIVE DATA
                where_conditions = [
                    "snapshot_date >= date('now', '-2 days')",
                    "media_type IN ('movie', 'tv')",
                    "popularity > 50",
                    "title NOT LIKE '%Lee Chae-dam%'",
                    "title NOT LIKE '%Nukitashi%'"
                ]                
                where_clause = " AND ".join(where_conditions)
                limit_clause = "LIMIT 100"
            
            # Build the final query
            latest_query = f"""
            WITH deduplicated_data AS (
                SELECT title, media_type, popularity, vote_average, imdb_id, production_companies,
                    ROW_NUMBER() OVER (PARTITION BY title, media_type ORDER BY popularity DESC, snapshot_time DESC) as rn
                FROM popularity_snapshots
                WHERE {where_clause}
            )
            SELECT title, media_type, popularity, vote_average, imdb_id, production_companies
            FROM deduplicated_data
            WHERE rn = 1
            ORDER BY popularity DESC
            {limit_clause}
            """
            
            # Execute query and convert to list of dictionaries
            cursor.execute(latest_query)
            results = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            top_trending = [dict(zip(columns, row)) for row in results]   

        except Exception as e:
            print(f"❌ Query error: {e}")
            # Fallback query
            basic_query = """
            WITH deduplicated_data AS (
                SELECT title, media_type, popularity, vote_average, imdb_id, production_companies,
                    ROW_NUMBER() OVER (PARTITION BY title, media_type ORDER BY popularity DESC, snapshot_time DESC) as rn
                FROM popularity_snapshots
                WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM popularity_snapshots)
                AND media_type IN ('movie', 'tv')
                AND popularity > 50
            )
            SELECT title, media_type, popularity, vote_average, imdb_id, production_companies
            FROM deduplicated_data
            WHERE rn = 1
            ORDER BY popularity DESC
            LIMIT 100
            """
            cursor.execute(basic_query)
            results = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            top_trending = [dict(zip(columns, row)) for row in results]
                  
        finally:
            conn.close()
        
        return {
            'total_snapshots': total_snapshots,
            'unique_items': unique_items,
            'top_trending': top_trending,
            'company_filters': company_filters if company_filters else []
        }    

    def get_production_companies(self):
        """Get list of all production companies with content counts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all individual company counts first
        cursor.execute("""
        SELECT DISTINCT production_companies FROM popularity_snapshots 
        WHERE production_companies IS NOT NULL AND production_companies != '[]'
        """)
        
        company_counts = {}
        
        for (companies_json,) in cursor.fetchall():
            try:
                company_list = json.loads(companies_json)
                for company in company_list:
                    if company and len(company.strip()) >= 3:
                        # Count unique titles for this company
                        cursor.execute("""
                        SELECT COUNT(DISTINCT title) FROM popularity_snapshots
                        WHERE production_companies LIKE ?
                        """, (f"%{company}%",))
                        count = cursor.fetchone()[0]
                        
                        if count >= 3:
                            company_counts[company] = count
            except:
                continue
        
        # Apply smart grouping for major studios
        grouped_counts = {}
        processed_companies = set()
        
        # Define major studio groupings
        studio_groups = {
            'Disney': [
                'Walt Disney Pictures',
                'Walt Disney Animation Studios', 
                'Walt Disney Productions',
                'Pixar Animation Studios',
                'Marvel Studios',
                'Walt Disney Company',
                'Lucasfilm',
                'Lucasfilm Ltd.',
                'Lucasfilm Ltd'
            ],
            'Warner Bros.': [
                'Warner Bros. Pictures',
                'Warner Bros.',
                'Warner Brothers',
                'New Line Cinema',
                'DC Films',
                'DC Entertainment',
                'Warner Bros. Animation',
                'Warner Bros. Television'
            ],
            'Universal': [
                'Universal Pictures',
                'Universal Studios',
                'NBCUniversal',
                'Focus Features',
                'Universal Television'
            ],
            'Paramount': [
                'Paramount Pictures',
                'Paramount Players',
                'Paramount Global',
                'Paramount'
            ],
            'Sony': [
                'Sony Pictures',
                'Sony Pictures Entertainment',
                'Columbia Pictures',
                'TriStar Pictures',
                'Sony Pictures Animation'
            ]
        }
        
        # Group major studios
        for group_name, company_names in studio_groups.items():
            total_count = 0
            for company_name in company_names:
                if company_name in company_counts:
                    total_count += company_counts[company_name]
                    processed_companies.add(company_name)
            
            if total_count > 0:
                grouped_counts[group_name] = total_count
        
        # Add remaining individual companies
        for company, count in company_counts.items():
            if company not in processed_companies:
                grouped_counts[company] = count

        # Remove fake companies
        grouped_counts.pop('Y Productions', None)
        grouped_counts.pop('ANIMA', None)
        grouped_counts.pop('anima', None)

        # Sort and return
        companies = sorted(grouped_counts.items(), key=lambda x: x[1], reverse=True)
        conn.close()
        return companies[:100]

def create_simple_chart_data(self, top_trending, media_type, company_filters=None):
    """Create simple HTML chart instead of plotly"""
    if not top_trending:
        return '<div class="no-data">No data available</div>'
    
    # Filter by media type and take top 10
    filtered_data = [item for item in top_trending if item.get('media_type') == media_type][:10]
    
    if not filtered_data:
        return f'<div class="no-data">No {media_type} data available</div>'
    
    # Create simple HTML bar chart
    html = '<div class="simple-chart">'
    max_popularity = max(item['popularity'] for item in filtered_data)
    
    for item in filtered_data:
        width_percent = (item['popularity'] / max_popularity) * 100
        html += f'''
        <div class="chart-row">
            <div class="chart-label">{item['title'][:30]}</div>
            <div class="chart-bar" style="width: {width_percent}%"></div>
            <div class="chart-value">{item['popularity']:.1f}</div>
        </div>
        '''
    
    html += '</div>'
    return html

# Initialize analyzer
analyzer = WebTrendAnalyzer()

@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard_with_companies.html')

@app.route('/api/dashboard-data')
def api_dashboard_data():
    """API endpoint for dashboard data"""
    try:
        companies_param = request.args.get('companies', 'all')
        
        # Parse company filters
        if companies_param == 'all' or not companies_param:
            company_filters = None
        else:
            company_filters = [c.strip() for c in companies_param.split(',') if c.strip()]
        
        # Get data with company filters
        data = analyzer.get_dashboard_data(company_filters)
        
        if not data['top_trending']:
            # Return empty response if no data
            companies_text = ', '.join(company_filters) if company_filters else 'selected companies'
            return jsonify({
                'success': False,
                'error': f'No content found for {companies_text}',
                'stats': {'total_snapshots': data['total_snapshots'], 'unique_items': data['unique_items']},
                'charts': {'top_movies': [], 'top_tv': []},
                'top_trending': [],
                'company_filters': company_filters
            })
        
        # Create simple chart data
        movies_chart = analyzer.create_simple_chart_data(data['top_trending'], 'movie', company_filters)
        tv_chart = analyzer.create_simple_chart_data(data['top_trending'], 'tv', company_filters)
        
        # Get recent trends (first 15 items)
        recent_trends = data['top_trending'][:15]
        
        return jsonify({
            'success': True,
            'stats': {
                'total_snapshots': data['total_snapshots'],
                'unique_items': data['unique_items'],
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'company_filters': company_filters,
                'filtered_results': len(data['top_trending'])
            },
            'charts': {
                'top_movies': movies_chart,
                'top_tv': tv_chart
            },
            'top_trending': recent_trends,
            'chart_html': {
                'movies': movies_chart,
                'tv': tv_chart
            }
        })        
    except Exception as e:
        print(f"❌ API Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/production-companies')
def api_production_companies():
    """API endpoint for production companies list"""
    try:
        companies = analyzer.get_production_companies()
        return jsonify({
            'success': True,
            'companies': companies
        })
    except Exception as e:
        print(f"❌ Companies API Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/search/<query>')
def search_content(query):
    """Search for content"""
    try:
        conn = sqlite3.connect(analyzer.db_path)
        cursor = conn.cursor()
        
        search_query = """
        SELECT title, media_type, popularity, vote_average, imdb_id, production_companies
        FROM popularity_snapshots
        WHERE title LIKE ?
        AND media_type IN ('movie', 'tv')
        AND popularity > 10
        ORDER BY popularity DESC
        LIMIT 20
        """
        
        search_param = f"%{query}%"
        cursor.execute(search_query, (search_param,))
        results = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        
        conn.close()
        
        if not results:
            return jsonify({'success': True, 'results': []})
        
        # Convert to list of dictionaries
        search_results = []
        for row in results:
            row_dict = dict(zip(columns, row))
            try:
                companies = json.loads(row_dict['production_companies']) if row_dict['production_companies'] else []
            except:
                companies = []
            
            search_results.append({
                'title': row_dict['title'],
                'media_type': row_dict['media_type'],
                'popularity': row_dict['popularity'],
                'vote_average': row_dict['vote_average'],
                'imdb_id': row_dict['imdb_id'],
                'production_companies': companies
            })
        
        return jsonify({'success': True, 'results': search_results})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print("🌐 Starting Movie Trends Web Server...")
    print("📊 Dashboard available")
    print("🔄 Press Ctrl+C to stop")
    
    # Use PORT environment variable for Render deployment
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)
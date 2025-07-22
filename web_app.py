# web_app.py
# Enhanced web interface with multi-select production company filtering

from flask import Flask, render_template, jsonify, request
import sqlite3
import json
import os
from datetime import datetime, timedelta
import plotly.graph_objs as go
import plotly.utils
import pandas as pd

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
            
            # Build the final query - FIXED DEDUPLICATION
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
            
            top_trending = pd.read_sql_query(latest_query, conn)
            
        except Exception as e:
            print(f"❌ Query error: {e}")
            # Fallback query that should show "How to Train Your Dragon"
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
            top_trending = pd.read_sql_query(basic_query, conn)
        
        finally:
            conn.close()
        
        return {
            'total_snapshots': total_snapshots,
            'unique_items': unique_items,
            'top_trending': top_trending,
            'company_filters': company_filters if company_filters else []
        }    

    def get_production_companies(self):
        """Get list of all production companies with content counts - FIXED GROUPING"""
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
                        
                        if count >= 3:  # Only include companies with 3+ items
                            company_counts[company] = count
            except:
                continue
        
        # Now apply smart grouping for major studios
        grouped_counts = {}
        processed_companies = set()
        
        # Define major studio groupings with exact company names
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
        
        # Add remaining individual companies (not part of major studio groups)
        for company, count in company_counts.items():
            if company not in processed_companies:
                grouped_counts[company] = count

        # Remove fake companies created by partial matching
        grouped_counts.pop('Y Productions', None)
        grouped_counts.pop('ANIMA', None)
        grouped_counts.pop('anima', None)

        # Sort and return
        companies = sorted(grouped_counts.items(), key=lambda x: x[1], reverse=True)
        conn.close()
        return companies[:100]

    def create_top_movies_chart(self, top_trending, company_filters=None):
        """Create bar chart of top trending movies only"""
        if top_trending.empty:
            return json.dumps({}, cls=plotly.utils.PlotlyJSONEncoder)
        
        try:
            # Filter for movies only and take top 10
            movies_only = top_trending[top_trending['media_type'] == 'movie'].head(10)
            
            if movies_only.empty:
                return json.dumps({}, cls=plotly.utils.PlotlyJSONEncoder)
            
            movies_reversed = movies_only.iloc[::-1]  # Reverse for proper display
            
            # Movie colors
            movie_colors = [
                '#FF6B6B', '#FF8E53', '#FF6B9D', '#C44569', '#F8B500',
                '#FF7675', '#E17055', '#D63031', '#A29BFE', '#6C5CE7'
            ]
            colors = movie_colors[:len(movies_reversed)][::-1]
            
            fig = go.Figure(data=[
                go.Bar(
                    x=movies_reversed['popularity'],
                    y=movies_reversed['title'],
                    orientation='h',
                    marker=dict(color=colors),
                    text=[f"{pop:.1f}" for pop in movies_reversed['popularity']],
                    textposition='auto',
                )
            ])
            
            # Dynamic title based on selected companies
            if company_filters and len(company_filters) > 0 and company_filters != ['all']:
                if len(company_filters) == 1:
                    title = f'🎬 Top 10 Movies - {company_filters[0]}'
                else:
                    title = f'🎬 Top 10 Movies - {len(company_filters)} Companies'
            else:
                title = '🎬 Top 10 Movies'
            
            fig.update_layout(
                title=title,
                xaxis_title='Popularity Score',
                yaxis_title='',
                template='plotly_white',
                height=500
            )
            
            return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
            
        except Exception as e:
            print(f"❌ Movies chart error: {e}")
            return json.dumps({}, cls=plotly.utils.PlotlyJSONEncoder)

    def create_top_tv_chart(self, top_trending, company_filters=None):
        """Create bar chart of top trending TV shows only"""
        if top_trending.empty:
            return json.dumps({}, cls=plotly.utils.PlotlyJSONEncoder)
        
        try:
            # Filter for TV shows only and take top 10
            tv_only = top_trending[top_trending['media_type'] == 'tv'].head(10) 
            
            if tv_only.empty:
                return json.dumps({}, cls=plotly.utils.PlotlyJSONEncoder)
            
            tv_reversed = tv_only.iloc[::-1]  # Reverse for proper display
            
            # TV colors
            tv_colors = [
                '#4ECDC4', '#45B7D1', '#96CEB4', '#3DC1D3', '#00D2D3',
                '#74B9FF', '#0984E3', '#00B894', '#55A3FF', '#26C6DA'
            ]
            colors = tv_colors[:len(tv_reversed)][::-1]
            
            fig = go.Figure(data=[
                go.Bar(
                    x=tv_reversed['popularity'],
                    y=tv_reversed['title'],
                    orientation='h',
                    marker=dict(color=colors),
                    text=[f"{pop:.1f}" for pop in tv_reversed['popularity']],
                    textposition='auto',
                )
            ])
            
            # Dynamic title based on selected companies  
            if company_filters and len(company_filters) > 0 and company_filters != ['all']:
                tv_count = len(tv_only)  # Get actual count
                if len(company_filters) == 1:
                    title = f'📺 Top {tv_count} TV Shows - {company_filters[0]}'
                else:
                    title = f'📺 Top {tv_count} TV Shows - {len(company_filters)} Companies'
            else:
                title = '📺 Top 10 TV Shows'
            
            fig.update_layout(
                title=title,
                xaxis_title='Popularity Score',
                yaxis_title='',
                template='plotly_white',
                height=500
            )
            
            return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
            
        except Exception as e:
            print(f"❌ TV chart error: {e}")
            return json.dumps({}, cls=plotly.utils.PlotlyJSONEncoder)
        
# Initialize analyzer
analyzer = WebTrendAnalyzer()

@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard_with_companies.html')

@app.route('/api/dashboard-data')
def api_dashboard_data():
    """API endpoint for dashboard data with optional company filters"""
    try:
        companies_param = request.args.get('companies', 'all')
        
        # Parse company filters
        if companies_param == 'all' or not companies_param:
            company_filters = None
        else:
            company_filters = [c.strip() for c in companies_param.split(',') if c.strip()]
        
        # Get data with company filters
        data = analyzer.get_dashboard_data(company_filters)
        
        if data['top_trending'].empty:
            # Return empty response if no data
            companies_text = ', '.join(company_filters) if company_filters else 'selected companies'
            return jsonify({
                'success': False,
                'error': f'No content found for {companies_text}',
                'stats': {'total_snapshots': data['total_snapshots'], 'unique_items': data['unique_items']},
                'charts': {'top_movies': '{}', 'top_tv': '{}'},
                'top_trending': [],
                'company_filters': company_filters
            })
        
        # Create charts with company filters
        movies_chart = analyzer.create_top_movies_chart(data['top_trending'], company_filters)
        tv_chart = analyzer.create_top_tv_chart(data['top_trending'], company_filters)
        
        # Get recent trends for trending list
        recent_trends = data['top_trending'].head(15)
        
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
            'top_trending': recent_trends.to_dict('records')
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
    try:
        analyzer = WebTrendAnalyzer()
        conn = sqlite3.connect(analyzer.db_path)
        
        # UPDATED SEARCH QUERY WITH DEDUPLICATION
        search_query = """
        WITH deduplicated_search AS (
            SELECT title, media_type, popularity, vote_average, imdb_id, production_companies,
            ROW_NUMBER() OVER (PARTITION BY title, media_type ORDER BY popularity DESC, snapshot_time DESC) as rn
            FROM popularity_snapshots
            WHERE title LIKE ?
            AND media_type IN ('movie', 'tv')
            AND popularity > 10
        )
        SELECT title, media_type, popularity, vote_average, imdb_id, production_companies
        FROM deduplicated_search
        WHERE rn = 1
        ORDER BY popularity DESC
        LIMIT 20
        """
        
        search_param = f"%{query}%"
        df = pd.read_sql_query(search_query, conn, params=(search_param,))
        conn.close()
        
        if df.empty:
            return jsonify({'success': True, 'results': []})
        
        # Process production companies for each result
        results = []
        for _, row in df.iterrows():
            try:
                companies = json.loads(row['production_companies']) if row['production_companies'] else []
            except:
                companies = []
            
            results.append({
                'title': row['title'],
                'media_type': row['media_type'],
                'popularity': row['popularity'],
                'vote_average': row['vote_average'],
                'imdb_id': row['imdb_id'],
                'production_companies': companies
            })
        
        return jsonify({'success': True, 'results': results})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print("🌐 Starting Enhanced Movie Trends Web Server...")
    print("📊 Dashboard with Multi-Select Production Company filter available at: http://localhost:8080")
    print("🔄 Press Ctrl+C to stop")
    app.run(debug=True, host='0.0.0.0', port=8080)
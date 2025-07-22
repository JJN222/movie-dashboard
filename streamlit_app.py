# streamlit_app.py
# Movie Trends Dashboard converted to Streamlit

import streamlit as st
import sqlite3
import json
import pandas as pd
import plotly.graph_objs as go
from datetime import datetime

# Configure page
st.set_page_config(
    page_title="🎬 Movie Trends Dashboard",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: 700;
        color: #1f1f1f;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .stSelectbox > div > div {
        background-color: #f0f2f6;
    }
</style>
""", unsafe_allow_html=True)

class MovieTrendAnalyzer:
    def __init__(self, db_path="movie_trends.db"):
        self.db_path = db_path
    
    @st.cache_data
    def get_dashboard_data(_self, company_filters=None):
        """Get all data needed for the dashboard with optional company filters"""
        conn = sqlite3.connect(_self.db_path)
        
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
                                company_filters != ['All Companies'])
            
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
                    if company and company != 'All Companies':
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
            
            top_trending = pd.read_sql_query(latest_query, conn)
            
        except Exception as e:
            st.error(f"Query error: {e}")
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
            top_trending = pd.read_sql_query(basic_query, conn)
        
        finally:
            conn.close()
        
        return {
            'total_snapshots': total_snapshots,
            'unique_items': unique_items,
            'top_trending': top_trending,
            'company_filters': company_filters if company_filters else []
        }
    
    @st.cache_data
    def get_production_companies(_self):
        """Get list of all production companies with content counts"""
        conn = sqlite3.connect(_self.db_path)
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
        
        studio_groups = {
            'Disney': [
                'Walt Disney Pictures', 'Walt Disney Animation Studios', 
                'Walt Disney Productions', 'Pixar Animation Studios',
                'Marvel Studios', 'Walt Disney Company',
                'Lucasfilm', 'Lucasfilm Ltd.', 'Lucasfilm Ltd'
            ],
            'Warner Bros.': [
                'Warner Bros. Pictures', 'Warner Bros.', 'Warner Brothers',
                'New Line Cinema', 'DC Films', 'DC Entertainment',
                'Warner Bros. Animation', 'Warner Bros. Television'
            ],
            'Universal': [
                'Universal Pictures', 'Universal Studios', 'NBCUniversal',
                'Focus Features', 'Universal Television'
            ],
            'Paramount': [
                'Paramount Pictures', 'Paramount Players',
                'Paramount Global', 'Paramount'
            ],
            'Sony': [
                'Sony Pictures', 'Sony Pictures Entertainment',
                'Columbia Pictures', 'TriStar Pictures', 'Sony Pictures Animation'
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
        return companies[:50]  # Top 50 for dropdown

def create_movie_chart(data):
    """Create movie chart"""
    movies = data[data['media_type'] == 'movie'].head(10)
    if movies.empty:
        return None
        
    fig = go.Figure(data=[
        go.Bar(
            x=movies['popularity'],
            y=movies['title'],
            orientation='h',
            marker=dict(color=['#FF6B6B', '#FF8E53', '#FF6B9D', '#C44569', '#F8B500',
                              '#FF7675', '#E17055', '#D63031', '#A29BFE', '#6C5CE7'][:len(movies)][::-1]),
            text=[f"{pop:.1f}" for pop in movies['popularity']],
            textposition='auto',
        )
    ])
    
    fig.update_layout(
        title='🎬 Top 10 Movies',
        xaxis_title='Popularity Score',
        yaxis_title='',
        height=500,
        yaxis={'categoryorder': 'total ascending'}
    )
    return fig

def create_tv_chart(data):
    """Create TV chart"""
    tv_shows = data[data['media_type'] == 'tv'].head(10)
    if tv_shows.empty:
        return None
        
    fig = go.Figure(data=[
        go.Bar(
            x=tv_shows['popularity'],
            y=tv_shows['title'],
            orientation='h',
            marker=dict(color=['#4ECDC4', '#45B7D1', '#96CEB4', '#3DC1D3', '#00D2D3',
                              '#74B9FF', '#0984E3', '#00B894', '#55A3FF', '#26C6DA'][:len(tv_shows)][::-1]),
            text=[f"{pop:.1f}" for pop in tv_shows['popularity']],
            textposition='auto',
        )
    ])
    
    fig.update_layout(
        title='📺 Top 10 TV Shows',
        xaxis_title='Popularity Score',
        yaxis_title='',
        height=500,
        yaxis={'categoryorder': 'total ascending'}
    )
    return fig

def display_trending_list(data):
    """Display trending content list"""
    st.subheader("📈 Currently Trending")
    
    # Search functionality
    search_query = st.text_input("🔍 Search movies & TV shows...", placeholder="Search for titles...")
    
    if search_query:
        filtered_data = data[data['title'].str.contains(search_query, case=False, na=False)]
    else:
        filtered_data = data.head(15)
    
    for idx, row in filtered_data.iterrows():
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            media_icon = "🎬" if row['media_type'] == 'movie' else "📺"
            imdb_link = f"https://www.imdb.com/title/{row['imdb_id']}/" if row['imdb_id'] else "#"
            
            if row['imdb_id']:
                st.markdown(f"**{media_icon} [{row['title']}]({imdb_link})**")
            else:
                st.markdown(f"**{media_icon} {row['title']}**")
            
            st.caption(f"{row['media_type'].upper()} • ⭐ {row['vote_average']:.1f}/10")
        
        with col2:
            st.metric("Popularity", f"{row['popularity']:.1f}")
        
        with col3:
            # Show production companies
            try:
                companies = json.loads(row['production_companies']) if row['production_companies'] else []
                if companies:
                    st.caption(f"🏭 {companies[0]}")
            except:
                pass

# Initialize analyzer
@st.cache_resource
def get_analyzer():
    return MovieTrendAnalyzer()

analyzer = get_analyzer()

# Main app
def main():
    # Header
    st.markdown('<h1 class="main-header">🎬 Movie & TV Trends Dashboard</h1>', unsafe_allow_html=True)
    st.markdown("Real-time entertainment analytics with production company insights")
    
    # Sidebar for filters
    st.sidebar.header("🏭 Production Companies")
    
    # Get companies
    companies_data = analyzer.get_production_companies()
    company_names = ['All Companies'] + [f"{name} ({count})" for name, count in companies_data]
    
    # Multi-select for companies
    selected_companies = st.sidebar.multiselect(
        "Select companies to filter:",
        options=company_names,
        default=['All Companies'],
        help="Choose one or more production companies to filter content"
    )
    
    # Extract company names (remove counts)
    if 'All Companies' in selected_companies or not selected_companies:
        company_filters = None
    else:
        company_filters = [comp.split(' (')[0] for comp in selected_companies]
    
    # Get dashboard data
    data = analyzer.get_dashboard_data(company_filters)
    
    # Stats row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📊 Total Data Points", f"{data['total_snapshots']:,}")
    
    with col2:
        st.metric("🎬 Tracked Items", f"{data['unique_items']:,}")
    
    with col3:
        st.metric("📈 Filtered Results", f"{len(data['top_trending']):,}")
    
    with col4:
        st.metric("🏭 Selected Companies", len(company_filters) if company_filters else 0)
    
    # Charts row
    if not data['top_trending'].empty:
        col1, col2 = st.columns(2)
        
        with col1:
            movie_chart = create_movie_chart(data['top_trending'])
            if movie_chart:
                st.plotly_chart(movie_chart, use_container_width=True)
            else:
                st.info("No movie data available for selected filters")
        
        with col2:
            tv_chart = create_tv_chart(data['top_trending'])
            if tv_chart:
                st.plotly_chart(tv_chart, use_container_width=True)
            else:
                st.info("No TV show data available for selected filters")
        
        # Trending list
        st.markdown("---")
        display_trending_list(data['top_trending'])
    
    else:
        st.warning("No data found for the selected filters. Try selecting different production companies.")
    
    # Footer
    st.markdown("---")
    st.markdown("**Last updated:** " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

if __name__ == "__main__":
    main()
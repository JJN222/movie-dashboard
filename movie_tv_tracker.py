# movie_tv_tracker.py
# Enhanced tracker with movies AND TV shows!

import requests
import json
from datetime import datetime
import time

# 🔑 Your API key
API_KEY = "1216ca271ce34811541580deeb170c2f"

class MovieTVTracker:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.themoviedb.org/3"
    
    def get_trending_content(self, content_type="all", time_window="day"):
        """
        Get trending content
        content_type: 'movie', 'tv', or 'all'
        time_window: 'day' or 'week'
        """
        print(f"📡 Getting trending {content_type} for the {time_window}...")
        
        url = f"{self.base_url}/trending/{content_type}/{time_window}"
        params = {'api_key': self.api_key}
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data['results']
            else:
                print(f"❌ Error {response.status_code}: {response.text}")
                return []
        except Exception as e:
            print(f"❌ Error: {e}")
            return []
    
    def display_content(self, content_list, title="TRENDING CONTENT"):
        """Display content in a nice format"""
        print(f"\n🔥 {title}")
        print("=" * 60)
        
        for i, item in enumerate(content_list[:10], 1):
            # Handle both movies and TV shows
            name = item.get('title') or item.get('name', 'Unknown')
            content_type = item.get('media_type', 'unknown')
            popularity = item.get('popularity', 0)
            rating = item.get('vote_average', 0)
            release_date = item.get('release_date') or item.get('first_air_date', 'Unknown')
            
            # Choose emoji based on type
            emoji = "🎬" if content_type == "movie" else "📺" if content_type == "tv" else "🎭"
            
            print(f"{i:2d}. {emoji} {name}")
            print(f"    📈 Popularity: {popularity:.1f}")
            print(f"    ⭐ Rating: {rating}/10")
            print(f"    📅 Released: {release_date}")
            print(f"    🏷️  Type: {content_type.title()}")
            print()
    
    def compare_movies_vs_tv(self):
        """Compare trending movies vs TV shows"""
        print("🎬 Getting trending movies...")
        movies = self.get_trending_content("movie", "day")
        time.sleep(0.5)  # Be nice to the API
        
        print("📺 Getting trending TV shows...")
        tv_shows = self.get_trending_content("tv", "day")
        time.sleep(0.5)
        
        # Display results
        if movies:
            self.display_content(movies, "TRENDING MOVIES TODAY")
        
        if tv_shows:
            self.display_content(tv_shows, "TRENDING TV SHOWS TODAY")
        
        # Quick comparison stats
        if movies and tv_shows:
            avg_movie_popularity = sum(m.get('popularity', 0) for m in movies) / len(movies)
            avg_tv_popularity = sum(t.get('popularity', 0) for t in tv_shows) / len(tv_shows)
            
            print(f"\n📊 QUICK STATS:")
            print(f"🎬 Average Movie Popularity: {avg_movie_popularity:.1f}")
            print(f"📺 Average TV Popularity: {avg_tv_popularity:.1f}")
            
            if avg_movie_popularity > avg_tv_popularity:
                print("🏆 Movies are trending higher today!")
            else:
                print("🏆 TV shows are trending higher today!")
        
        return movies, tv_shows
    
    def find_sudden_spikes(self):
        """Find content that's hot today but not in weekly trends"""
        print("🔍 Looking for sudden popularity spikes...")
        
        daily_trends = self.get_trending_content("all", "day")
        time.sleep(0.5)
        weekly_trends = self.get_trending_content("all", "week")
        
        # Create sets of titles for comparison
        daily_titles = {(item.get('title') or item.get('name')): item for item in daily_trends}
        weekly_titles = {(item.get('title') or item.get('name')): item for item in weekly_trends}
        
        # Find items that are hot today but not in weekly (sudden spikes)
        sudden_spikes = []
        for title, item in daily_titles.items():
            if title not in weekly_titles:
                sudden_spikes.append(item)
        
        if sudden_spikes:
            self.display_content(sudden_spikes, "🚀 SUDDEN SPIKES (Hot today, not in weekly trends)")
        else:
            print("📊 No sudden spikes detected today")
        
        return sudden_spikes
    
    def save_comprehensive_report(self, movies, tv_shows, all_content, spikes):
        """Save a comprehensive report"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_trending": len(all_content),
                "trending_movies": len(movies),
                "trending_tv_shows": len(tv_shows),
                "sudden_spikes": len(spikes)
            },
            "movies": movies,
            "tv_shows": tv_shows,
            "all_content": all_content,
            "sudden_spikes": spikes
        }
        
        filename = f"comprehensive_report_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"💾 Comprehensive report saved to {filename}")
        return filename

# 🚀 Main program
def main():
    print("🎭 Enhanced Movie & TV Tracker Starting...")
    print("=" * 50)
    
    # Create our tracker
    tracker = MovieTVTracker(API_KEY)
    
    # Get all trending content first
    print("📊 Getting all trending content...")
    all_trending = tracker.get_trending_content("all", "day")
    
    if not all_trending:
        print("😞 No data received. Check your API key!")
        return
    
    # Display overall trends
    tracker.display_content(all_trending, "ALL TRENDING CONTENT TODAY")
    
    # Compare movies vs TV shows
    print("\n" + "="*50)
    movies, tv_shows = tracker.compare_movies_vs_tv()
    
    # Look for sudden spikes
    print("\n" + "="*50)
    spikes = tracker.find_sudden_spikes()
    
    # Save comprehensive report
    report_file = tracker.save_comprehensive_report(movies, tv_shows, all_trending, spikes)
    
    # Final summary
    print(f"\n✨ Analysis Complete!")
    print(f"📄 Full report: {report_file}")
    print(f"📊 Total trending items: {len(all_trending)}")
    print(f"🎬 Movies: {len(movies)}")
    print(f"📺 TV Shows: {len(tv_shows)}")
    print(f"🚀 Sudden spikes: {len(spikes)}")

if __name__ == "__main__":
    main()
# simple_movie_tracker.py
# Your first movie trending tracker!

import requests
import json
from datetime import datetime

# 🔑 Your TMDb API key
API_KEY = "1216ca271ce34811541580deeb170c2f"

def get_trending_movies():
    """Get today's trending movies"""
    print("🎬 Getting trending movies...")
    
    # TMDb API endpoint for trending movies
    url = f"https://api.themoviedb.org/3/trending/movie/day?api_key={API_KEY}"
    
    try:
        # Make the request to TMDb
        response = requests.get(url)
        
        # Check if request was successful
        if response.status_code == 200:
            data = response.json()
            movies = data['results']
            
            print(f"✅ Found {len(movies)} trending movies!")
            return movies
        else:
            print(f"❌ Error: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Something went wrong: {e}")
        return []

def display_movies(movies):
    """Display the movies in a nice format"""
    print("\n🔥 TODAY'S TRENDING MOVIES:")
    print("=" * 50)
    
    for i, movie in enumerate(movies[:10], 1):  # Show top 10
        title = movie.get('title', 'Unknown Title')
        popularity = movie.get('popularity', 0)
        rating = movie.get('vote_average', 0)
        release_date = movie.get('release_date', 'Unknown')
        
        print(f"{i:2d}. {title}")
        print(f"    📈 Popularity: {popularity:.1f}")
        print(f"    ⭐ Rating: {rating}/10")
        print(f"    📅 Released: {release_date}")
        print()

def save_to_file(movies):
    """Save the data to a file"""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"trending_movies_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(movies, f, indent=2)
    
    print(f"💾 Saved data to {filename}")

# 🚀 Main program starts here
if __name__ == "__main__":
    print("🎭 Movie Trends Tracker Starting...")
    print("=" * 40)
    
    # Step 1: Get trending movies
    trending_movies = get_trending_movies()
    
    # Step 2: Display them
    if trending_movies:
        display_movies(trending_movies)
        
        # Step 3: Save to file
        save_to_file(trending_movies)
        
        print("\n✨ Done! Check the saved file for full data.")
    else:
        print("😞 No movies found. Check your API key!")
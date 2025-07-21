# auto_collector.py
# Automatically collect trend data at scheduled intervals

import schedule
import time
import subprocess
import os
from datetime import datetime

def collect_trending_data():
    """Run the trend detector and log results"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"🕐 [{timestamp}] Running trend collection...")
    
    try:
        # Run your trend detector
        result = subprocess.run(
            ["python3", "trend_detector.py"], 
            capture_output=True, 
            text=True,
            cwd=os.getcwd()
        )
        
        if result.returncode == 0:
            print(f"✅ [{timestamp}] Data collection successful!")
            
            # Log success
            with open("collection_log.txt", "a") as f:
                f.write(f"{timestamp}: SUCCESS\n")
        else:
            print(f"❌ [{timestamp}] Collection failed: {result.stderr}")
            
            # Log error
            with open("collection_log.txt", "a") as f:
                f.write(f"{timestamp}: ERROR - {result.stderr}\n")
                
    except Exception as e:
        print(f"❌ [{timestamp}] Exception: {e}")

def main():
    print("🤖 Auto Trend Collector Starting...")
    print("=" * 40)
    
    # Schedule data collection
    # Collect every 4 hours
    schedule.every(4).hours.do(collect_trending_data)
    
    # Also collect once daily at 9 AM
    schedule.every().day.at("09:00").do(collect_trending_data)
    
    # Run once immediately
    collect_trending_data()
    
    print("⏰ Scheduled collections:")
    print("   🕘 Every 4 hours")
    print("   🕘 Daily at 9:00 AM")
    print("\nPress Ctrl+C to stop...")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        print("\n👋 Auto collector stopped!")

if __name__ == "__main__":
    # Install schedule if needed
    try:
        import schedule
        main()
    except ImportError:
        print("📦 Installing schedule package...")
        import subprocess
        subprocess.check_call(["pip", "install", "schedule"])
        print("✅ Package installed! Run the script again.")
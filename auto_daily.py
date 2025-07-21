# auto_daily.py
# Run daily collection automatically every 24 hours

import schedule
import time
from daily_collector import DailyCollector

def run_daily_collection():
    print("🕐 Starting scheduled daily collection...")
    collector = DailyCollector()
    collector.run_daily_collection()
    print("✅ Scheduled collection complete!")

# Schedule to run every day at 6 AM
schedule.every().day.at("06:00").do(run_daily_collection)

print("⏰ Daily collector scheduled for 6:00 AM every day")
print("🚀 Running initial collection now...")

# Run once immediately
run_daily_collection()

print("⌛ Waiting for next scheduled run...")
print("Press Ctrl+C to stop")

while True:
    schedule.run_pending()
    time.sleep(3600)  # Check every hour
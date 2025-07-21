# auto_mass_collector.py
# Automatically collect thousands of items daily

import schedule
import time
from mass_collector import MassCollector

def daily_mass_collection():
    print("🕐 Running daily mass collection...")
    collector = MassCollector()
    collector.collect_comprehensive_data()
    print("✅ Daily collection complete!")

# Schedule daily collection at 6 AM
schedule.every().day.at("06:00").do(daily_mass_collection)

# Run once immediately
daily_mass_collection()

print("⏰ Scheduled daily mass collection at 6:00 AM")
print("Press Ctrl+C to stop")

while True:
    schedule.run_pending()
    time.sleep(3600)  # Check every hour
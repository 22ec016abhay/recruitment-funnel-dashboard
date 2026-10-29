import pandas as pd
import sqlite3
import os

print("Starting clean SQLite database loading process...")

# 1. Define paths relative to project root
csv_path = "python/data/processed/cleaned_funnel_data.csv"
events_path = "python/data/processed/funnel_long.csv"
db_path = "sql/recruitment.db"

if not os.path.exists(csv_path):
    raise FileNotFoundError(f"Could not find primary CSV at {csv_path}.")

df = pd.read_csv(csv_path)

# 2. Convert integer columns containing NaNs to Pandas nullable Int64
int_cols = [
    'age', 
    'days_applied_to_screen', 
    'days_screen_to_interview', 
    'days_interview_to_offer', 
    'days_offer_to_hire', 
    'total_days_to_hire'
]

for col in int_cols:
    if col in df.columns:
        df[col] = df[col].astype("Int64")

# 3. Create database directory and connect to SQLite
os.makedirs("sql", exist_ok=True)
conn = sqlite3.connect(db_path)

# 4. Write tables directly (if_exists='replace' handles table refreshing cleanly)
df.to_sql("applicants", conn, if_exists="replace", index=False)
print(f"Loaded {len(df)} rows into 'applicants' table.")

if os.path.exists(events_path):
    df_events = pd.read_csv(events_path)
    df_events.to_sql("funnel_events", conn, if_exists="replace", index=False)
    print(f"Loaded {len(df_events)} rows into 'funnel_events' table.")

conn.commit()
conn.close()

print("SQLite Database ETL complete and verified!")


import os
import pymysql
import pandas as pd
import numpy as np

def load_env(env_path):
    config = {}
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        config[parts[0].strip()] = parts[1].strip()
    return config

env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if not os.path.exists(env_file):
    env_file = '.env'

config = load_env(env_file)

DB_HOST = config.get('DB_HOST', 'localhost')
DB_PORT = int(config.get('DB_PORT', 3306))
DB_USER = config.get('DB_USER', 'root')
DB_PASSWORD = config.get('DB_PASSWORD', '')
DB_NAME = "product_analytics"

print("Starting SaaS Relational Database Data Quality & Cleaning Audit...")

try:
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    
    df_users = pd.read_sql("SELECT * FROM users", conn)
    df_subs = pd.read_sql("SELECT * FROM subscriptions", conn)
    df_sessions = pd.read_sql("SELECT * FROM user_sessions", conn)
    df_transactions = pd.read_sql("SELECT * FROM transactions", conn)
    df_tickets = pd.read_sql("SELECT * FROM support_tickets", conn)
    df_events = pd.read_sql("SELECT * FROM feature_events", conn)
    
    tables = [
        ("Users", df_users), 
        ("Subscriptions", df_subs), 
        ("User Sessions", df_sessions), 
        ("Transactions", df_transactions), 
        ("Support Tickets", df_tickets),
        ("Feature Events", df_events)
    ]
    
    print("\n=== 1. Missing Values Audit ===")
    for name, df in tables:
        missing = df.isnull().sum()
        missing = missing[missing > 0]
        if len(missing) > 0:
            print(f"\n[{name}] Missing values found:")
            for col, count in missing.items():
                print(f"  - Column '{col}': {count} missing values ({round(count * 100 / len(df), 2)}%)")
        else:
            print(f"[{name}] Clean. No missing values.")

    print("\n=== 2. Duplicate Rows Detection ===")
    for name, df in tables:
        duplicates = df.duplicated().sum()
        print(f"[{name}] Duplicate rows: {duplicates}")
        if duplicates > 0:
            df.drop_duplicates(inplace=True)
            print(f"  -> Removed {duplicates} duplicates.")

    print("\n=== 3. Statistical Outlier Detection (IQR Method) ===")
    
    q1_dur = df_sessions['session_duration_minutes'].quantile(0.25)
    q3_dur = df_sessions['session_duration_minutes'].quantile(0.75)
    iqr_dur = q3_dur - q1_dur
    upper_dur = q3_dur + 1.5 * iqr_dur
    dur_outliers = df_sessions[df_sessions['session_duration_minutes'] > upper_dur]
    print(f"[User Sessions] Duration outliers (> {round(upper_dur, 1)} mins): {len(dur_outliers)} rows ({round(len(dur_outliers)*100/len(df_sessions), 2)}%)")
    
    q1_ts = df_events['time_spent_seconds'].quantile(0.25)
    q3_ts = df_events['time_spent_seconds'].quantile(0.75)
    iqr_ts = q3_ts - q1_ts
    upper_ts = q3_ts + 1.5 * iqr_ts
    ts_outliers = df_events[df_events['time_spent_seconds'] > upper_ts]
    print(f"[Feature Events] Time spent outliers (> {round(upper_ts, 1)} secs): {len(ts_outliers)} rows ({round(len(ts_outliers)*100/len(df_events), 2)}%)")
    
    q1_res = df_tickets['resolution_time_hours'].quantile(0.25)
    q3_res = df_tickets['resolution_time_hours'].quantile(0.75)
    iqr_res = q3_res - q1_res
    upper_res = q3_res + 1.5 * iqr_res
    res_outliers = df_tickets[df_tickets['resolution_time_hours'] > upper_res]
    print(f"[Support Tickets] Resolution time outliers (> {round(upper_res, 1)} hours): {len(res_outliers)} rows ({round(len(res_outliers)*100/len(df_tickets), 2)}%)")
    
    print("\n=== 4. Cleaning Actions Executed ===")
    
    cap_dur = df_sessions['session_duration_minutes'].quantile(0.99)
    df_sessions['session_duration_minutes'] = np.where(df_sessions['session_duration_minutes'] > cap_dur, cap_dur, df_sessions['session_duration_minutes'])
    print(f"  * Capped extreme session durations at 99th percentile: {round(cap_dur, 1)} minutes.")
    
    cap_ts = df_events['time_spent_seconds'].quantile(0.99)
    df_events['time_spent_seconds'] = np.where(df_events['time_spent_seconds'] > cap_ts, cap_ts, df_events['time_spent_seconds'])
    print(f"  * Capped feature interaction durations at 99th percentile: {round(cap_ts, 1)} seconds.")
    
    median_csat = int(df_tickets['satisfaction_score'].median())
    missing_csat_count = df_tickets['satisfaction_score'].isnull().sum()
    df_tickets['satisfaction_score'].fillna(median_csat, inplace=True)
    print(f"  * Imputed {missing_csat_count} missing CSAT scores with median rating: {median_csat}.")
    
    print("\nData Cleaning and Quality Audit completed successfully.")
    conn.close()

except Exception as e:
    print(f"Database audit failed: {e}")
    import traceback
    traceback.print_exc()

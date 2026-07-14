import os
import sys
import random
import datetime
import pymysql
import pandas as pd
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    import config
except ImportError:
    import product_analytics_dashboard.config as config

def load_env(env_path):
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        env_vars[parts[0].strip()] = parts[1].strip()
    return env_vars

env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if not os.path.exists(env_file):
    env_file = '.env'

db_config = load_env(env_file)

DB_HOST = db_config.get('DB_HOST', 'localhost')
DB_PORT = int(db_config.get('DB_PORT', 3306))
DB_USER = db_config.get('DB_USER', 'root')
DB_PASSWORD = db_config.get('DB_PASSWORD', '')
DB_NAME = config.DATABASE_NAME

print(f"Connecting to MySQL at {DB_HOST}:{DB_PORT} as {DB_USER}...")

try:
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        autocommit=True
    )
    cursor = conn.cursor()
    
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME};")
    cursor.execute(f"USE {DB_NAME};")
    print(f"Database '{DB_NAME}' verified/created.")
    
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
    cursor.execute("DROP TABLE IF EXISTS feature_events;")
    cursor.execute("DROP TABLE IF EXISTS support_tickets;")
    cursor.execute("DROP TABLE IF EXISTS transactions;")
    cursor.execute("DROP TABLE IF EXISTS user_sessions;")
    cursor.execute("DROP TABLE IF EXISTS subscriptions;")
    cursor.execute("DROP TABLE IF EXISTS users;")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
    print("Dropped old tables.")
    
    cursor.execute("""
    CREATE TABLE users (
        user_id INT AUTO_INCREMENT PRIMARY KEY,
        signup_date DATE NOT NULL,
        signup_channel VARCHAR(50) NOT NULL,
        age INT NOT NULL,
        country VARCHAR(50) NOT NULL,
        experiment_group VARCHAR(10) NOT NULL,
        funnel_stage VARCHAR(30) NOT NULL
    );
    """)
    
    cursor.execute("""
    CREATE TABLE subscriptions (
        subscription_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        plan_type VARCHAR(50) NOT NULL,
        start_date DATE NOT NULL,
        end_date DATE DEFAULT NULL,
        status VARCHAR(20) NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
    );
    """)
    
    cursor.execute("""
    CREATE TABLE user_sessions (
        session_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        session_date DATE NOT NULL,
        session_duration_minutes INT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
    );
    """)
    
    cursor.execute("""
    CREATE TABLE transactions (
        transaction_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        transaction_date DATE NOT NULL,
        amount DECIMAL(10, 2) NOT NULL,
        status VARCHAR(20) NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
    );
    """)
    
    cursor.execute("""
    CREATE TABLE support_tickets (
        ticket_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        ticket_date DATE NOT NULL,
        category VARCHAR(50) NOT NULL,
        resolution_time_hours DECIMAL(5, 2) NOT NULL,
        satisfaction_score INT DEFAULT NULL,
        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
    );
    """)
    
    cursor.execute("""
    CREATE TABLE feature_events (
        event_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        feature_name VARCHAR(100) NOT NULL,
        event_time DATETIME NOT NULL,
        time_spent_seconds INT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
    );
    """)
    print("Database tables created in MySQL.")
    
    print("Generating simulated SaaS database...")
    random.seed(config.RANDOM_SEED)
    
    start_date = datetime.datetime.strptime(config.START_DATE_STR, "%Y-%m-%d").date()
    end_date = datetime.datetime.strptime(config.END_DATE_STR, "%Y-%m-%d").date()
    total_days = (end_date - start_date).days
    
    user_list = []
    num_users = config.NUM_USERS
    funnel_stages = ['Signup', 'Email Verification', 'First Login', 'Feature Adoption', 'Subscription', 'Renewal']
    
    for u_id in range(1, num_users + 1):
        signup_days = random.randint(0, total_days - 60)
        u_signup = start_date + datetime.timedelta(days=signup_days)
        u_channel = random.choices(config.ACQUISITION_CHANNELS, weights=config.ACQUISITION_WEIGHTS)[0]
        u_country = random.choices(config.COUNTRIES, weights=config.COUNTRY_WEIGHTS)[0]
        u_age = random.randint(18, 65)
        u_group = 'B' if random.random() < 0.5 else 'A'
        
        if u_group == 'B':
            u_stage = random.choices(funnel_stages, weights=[0.02, 0.02, 0.03, 0.33, 0.35, 0.25])[0]
        else:
            u_stage = random.choices(funnel_stages, weights=[0.05, 0.05, 0.06, 0.49, 0.20, 0.15])[0]
            
        user_list.append({
            'user_id': u_id,
            'signup_date': u_signup,
            'signup_channel': u_channel,
            'age': u_age,
            'country': u_country,
            'experiment_group': u_group,
            'funnel_stage': u_stage
        })
        
    print(f"Generated {num_users} users in memory.")
    
    subs_list = []
    sessions_list = []
    transactions_list = []
    tickets_list = []
    features_list = []
    
    for u in user_list:
        u_id = u['user_id']
        signup = u['signup_date']
        stage = u['funnel_stage']
        group = u['experiment_group']
        channel = u['signup_channel']
        
        plan = 'Free'
        if stage in ['Subscription', 'Renewal']:
            plan = random.choices(['Pro', 'Enterprise'], weights=[0.8, 0.2])[0]
            
        is_churned = stage not in ['Subscription', 'Renewal'] and random.random() < 0.85
        active_days = (end_date - signup).days
        if is_churned:
            active_days = random.randint(5, min(90, active_days))
            
        limit_date = signup + datetime.timedelta(days=active_days)
        
        sub_status = 'Active'
        if is_churned:
            sub_status = 'Churned'
        elif stage == 'Subscription':
            sub_status = 'Expired'
            
        sub_end_date = limit_date if sub_status in ['Churned', 'Expired'] else None
        subs_list.append({
            'user_id': u_id,
            'plan_type': plan,
            'start_date': signup,
            'end_date': sub_end_date,
            'status': sub_status
        })
        
        if stage in ['Signup', 'Email Verification']:
            continue
            
        if stage == 'First Login':
            sessions_list.append({
                'user_id': u_id,
                'session_date': signup,
                'session_duration_minutes': random.randint(2, 10)
            })
            continue
            
        base_login_rate = 0.12
        if group == 'B':
            base_login_rate += 0.05
        if channel == 'Referral':
            base_login_rate += 0.03
            
        for day in range(active_days + 1):
            log_date = signup + datetime.timedelta(days=day)
            
            login_prob = base_login_rate
            if is_churned and (limit_date - log_date).days < 14:
                login_prob *= 0.15
                
            if random.random() < login_prob:
                sess_dur = random.randint(5, 45)
                if group == 'B':
                    sess_dur += random.randint(2, 10)
                sessions_list.append({
                    'user_id': u_id,
                    'session_date': log_date,
                    'session_duration_minutes': sess_dur
                })
                
                if random.random() < 0.58:
                    feat = random.choice(config.FEATURES)
                    if plan != 'Free':
                        feat = random.choices(config.FEATURES, weights=[0.1, 0.2, 0.3, 0.1, 0.1, 0.2])[0]
                    else:
                        feat = random.choices(config.FEATURES, weights=[0.3, 0.05, 0.05, 0.2, 0.3, 0.1])[0]
                        
                    event_dt = datetime.datetime.combine(log_date, datetime.time(random.randint(0, 23), random.randint(0, 59)))
                    features_list.append({
                        'user_id': u_id,
                        'feature_name': feat,
                        'event_time': event_dt,
                        'time_spent_seconds': random.randint(5, 120)
                    })
                    
        if plan != 'Free':
            price = config.PLAN_PRICING[plan]
            curr_tx_date = signup
            tx_months = 1 if stage == 'Subscription' else (active_days // 30 + 1)
            
            for m in range(tx_months):
                tx_date = curr_tx_date + datetime.timedelta(days=m * 30)
                if tx_date > end_date:
                    break
                    
                fail_prob = 0.03 if group == 'B' else 0.08
                if is_churned and m == tx_months - 1:
                    fail_prob = 0.45
                    
                tx_status = 'Success'
                if random.random() < fail_prob:
                    tx_status = 'Failed'
                elif is_churned and m == tx_months - 1 and random.random() < 0.10:
                    tx_status = 'Refunded'
                    
                transactions_list.append({
                    'user_id': u_id,
                    'transaction_date': tx_date,
                    'amount': price,
                    'status': tx_status
                })
                
        ticket_prob = 0.18 if not is_churned else 0.45
        if channel == 'Referral':
            ticket_prob -= 0.06
            
        if random.random() < ticket_prob:
            num_tickets = random.randint(1, 2) if not is_churned else random.randint(2, 4)
            for _ in range(num_tickets):
                ticket_days = random.randint(0, active_days)
                t_date = signup + datetime.timedelta(days=ticket_days)
                t_category = random.choice(config.SUPPORT_CATEGORIES)
                
                if group == 'B':
                    res_time = round(random.uniform(0.5, 10.0), 2)
                    sat_score = random.choices([4, 5, 3], weights=[0.5, 0.4, 0.1])[0]
                else:
                    res_time = round(random.uniform(1.0, 36.0), 2)
                    sat_score = random.choices([3, 4, 2, 5, 1], weights=[0.3, 0.3, 0.2, 0.1, 0.1])[0]
                    
                if is_churned and random.random() < 0.5:
                    res_time = round(random.uniform(24.0, 72.0), 2)
                    sat_score = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]
                    
                tickets_list.append({
                    'user_id': u_id,
                    'ticket_date': t_date,
                    'category': t_category,
                    'resolution_time_hours': res_time,
                    'satisfaction_score': sat_score
                })
                
    df_u = pd.DataFrame(user_list)
    df_s = pd.DataFrame(subs_list)
    df_sess = pd.DataFrame(sessions_list)
    df_t = pd.DataFrame(transactions_list)
    df_tk = pd.DataFrame(tickets_list)
    df_fe = pd.DataFrame(features_list)
    
    print("\nGenerated dataset sizes:")
    print(f"  Users: {len(df_u)}")
    print(f"  Subscriptions: {len(df_s)}")
    print(f"  Sessions: {len(df_sess)}")
    print(f"  Feature Events: {len(df_fe)}")
    print(f"  Transactions: {len(df_t)}")
    print(f"  Support Tickets: {len(df_tk)}")
    
    os.makedirs('data', exist_ok=True)
    df_u.to_csv('data/users.csv', index=False)
    df_s.to_csv('data/subscriptions.csv', index=False)
    df_sess.to_csv('data/user_sessions.csv', index=False)
    df_t.to_csv('data/transactions.csv', index=False)
    df_tk.to_csv('data/support_tickets.csv', index=False)
    df_fe.to_csv('data/feature_events.csv', index=False)
    print("\nBackup CSV files exported to data/ folder.")
    
    print("\nBulk loading data into MySQL...")
    batch_size = 15000
    
    users_insert_data = [tuple(x) for x in df_u[['signup_date', 'signup_channel', 'age', 'country', 'experiment_group', 'funnel_stage']].values]
    cursor.executemany("""
    INSERT INTO users (signup_date, signup_channel, age, country, experiment_group, funnel_stage)
    VALUES (%s, %s, %s, %s, %s, %s)
    """, users_insert_data)
    
    subs_insert_data = [tuple(x) for x in df_s[['user_id', 'plan_type', 'start_date', 'end_date', 'status']].values]
    subs_insert_data = [(x[0], x[1], x[2], None if pd.isnull(x[3]) else x[3], x[4]) for x in subs_insert_data]
    cursor.executemany("""
    INSERT INTO subscriptions (user_id, plan_type, start_date, end_date, status)
    VALUES (%s, %s, %s, %s, %s)
    """, subs_insert_data)
    
    sess_insert_data = [tuple(x) for x in df_sess[['user_id', 'session_date', 'session_duration_minutes']].values]
    for i in range(0, len(sess_insert_data), batch_size):
        cursor.executemany("""
        INSERT INTO user_sessions (user_id, session_date, session_duration_minutes)
        VALUES (%s, %s, %s)
        """, sess_insert_data[i:i+batch_size])
        
    tx_insert_data = [tuple(x) for x in df_t[['user_id', 'transaction_date', 'amount', 'status']].values]
    for i in range(0, len(tx_insert_data), batch_size):
        cursor.executemany("""
        INSERT INTO transactions (user_id, transaction_date, amount, status)
        VALUES (%s, %s, %s, %s)
        """, tx_insert_data[i:i+batch_size])
        
    tk_insert_data = [tuple(x) for x in df_tk[['user_id', 'ticket_date', 'category', 'resolution_time_hours', 'satisfaction_score']].values]
    for i in range(0, len(tk_insert_data), batch_size):
        cursor.executemany("""
        INSERT INTO support_tickets (user_id, ticket_date, category, resolution_time_hours, satisfaction_score)
        VALUES (%s, %s, %s, %s, %s)
        """, tk_insert_data[i:i+batch_size])
        
    fe_insert_data = [tuple(x) for x in df_fe[['user_id', 'feature_name', 'event_time', 'time_spent_seconds']].values]
    for i in range(0, len(fe_insert_data), batch_size):
        cursor.executemany("""
        INSERT INTO feature_events (user_id, feature_name, event_time, time_spent_seconds)
        VALUES (%s, %s, %s, %s)
        """, fe_insert_data[i:i+batch_size])
        
    conn.commit()
    print("MySQL database populated successfully!")
    
    cursor.close()
    conn.close()

except Exception as e:
    print(f"Data generation failed: {e}")
    import traceback
    traceback.print_exc()

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

def run_metrics_pipeline():
    print("Executing SaaS Product Metrics Engine...")
    
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
        
        conn.close()
        
        df_users['signup_date'] = pd.to_datetime(df_users['signup_date'])
        df_subs['start_date'] = pd.to_datetime(df_subs['start_date'])
        df_subs['end_date'] = pd.to_datetime(df_subs['end_date'])
        df_sessions['session_date'] = pd.to_datetime(df_sessions['session_date'])
        df_transactions['transaction_date'] = pd.to_datetime(df_transactions['transaction_date'])
        
        dau = df_sessions.groupby('session_date')['user_id'].nunique().mean()
        df_sessions['year_month'] = df_sessions['session_date'].dt.to_period('M')
        mau = df_sessions.groupby('year_month')['user_id'].nunique().mean()
        stickiness = (dau / mau * 100) if mau > 0 else 0
        
        target_month = pd.Period('2026-06', freq='M')
        churned_in_month = df_subs[(df_subs['status'] == 'Churned') & (df_subs['end_date'].dt.to_period('M') == target_month)].shape[0]
        active_at_start = df_subs[
            (df_subs['start_date'] < '2026-06-01') & 
            ((df_subs['status'] == 'Active') | (df_subs['end_date'] >= '2026-06-01'))
        ].shape[0]
        churn_rate = (churned_in_month / active_at_start * 100) if active_at_start > 0 else 0
        
        june_revenue = df_transactions[
            (df_transactions['status'] == 'Success') & 
            (df_transactions['transaction_date'].dt.to_period('M') == target_month)
        ]['amount'].sum()
        
        june_mau = df_sessions[df_sessions['year_month'] == target_month]['user_id'].nunique()
        arpu = june_revenue / june_mau if june_mau > 0 else 0
        clv = arpu * (1 / (churn_rate / 100)) if churn_rate > 0 else 0
        
        signup_total = df_users.shape[0]
        login_total = df_users[df_users['funnel_stage'].isin(['First Login', 'Feature Adoption', 'Subscription', 'Renewal'])].shape[0]
        paid_total = df_users[df_users['funnel_stage'].isin(['Subscription', 'Renewal'])].shape[0]
        renewal_total = df_users[df_users['funnel_stage'] == 'Renewal'].shape[0]
        
        signup_to_login = (login_total / signup_total * 100) if signup_total > 0 else 0
        login_to_paid = (paid_total / login_total * 100) if login_total > 0 else 0
        paid_to_renewal = (renewal_total / paid_total * 100) if paid_total > 0 else 0
        
        ab_metrics = []
        for grp in ['A', 'B']:
            grp_users = df_users[df_users['experiment_group'] == grp]
            grp_u_ids = grp_users['user_id'].tolist()
            
            grp_signup = len(grp_users)
            grp_paid = len(grp_users[grp_users['funnel_stage'].isin(['Subscription', 'Renewal'])])
            grp_conv = (grp_paid / grp_signup * 100) if grp_signup > 0 else 0
            
            grp_rev = df_transactions[
                (df_transactions['status'] == 'Success') & 
                (df_transactions['user_id'].isin(grp_u_ids))
            ]['amount'].sum()
            grp_arpu = grp_rev / grp_signup if grp_signup > 0 else 0
            
            grp_sess_len = df_sessions[df_sessions['user_id'].isin(grp_u_ids)]['session_duration_minutes'].mean()
            
            grp_ret = df_sessions[
                (df_sessions['session_date'] >= '2026-06-01') & 
                (df_sessions['user_id'].isin(grp_u_ids))
            ]['user_id'].nunique()
            grp_ret_rate = (grp_ret / grp_signup * 100) if grp_signup > 0 else 0
            
            ab_metrics.append({
                'Group': grp,
                'Users': grp_signup,
                'Conversion_Rate': grp_conv,
                'Revenue_Per_User': grp_arpu,
                'Avg_Session_Duration_Mins': grp_sess_len,
                'Retention_Rate': grp_ret_rate
            })
            
        df_ab = pd.DataFrame(ab_metrics)
        
        df_users['signup_cohort'] = df_users['signup_date'].dt.to_period('M')
        df_cohort = pd.merge(df_users, df_sessions, on='user_id')
        df_cohort['activity_month'] = df_cohort['session_date'].dt.to_period('M')
        df_cohort['cohort_period'] = (df_cohort['activity_month'] - df_cohort['signup_cohort']).apply(lambda attr: attr.n)
        
        cohort_groups = df_cohort.groupby(['signup_cohort', 'cohort_period'])['user_id'].nunique()
        cohort_pivot = cohort_groups.unstack(1)
        cohort_sizes = cohort_pivot.iloc[:, 0]
        retention_matrix = cohort_pivot.divide(cohort_sizes, axis=0) * 100
        
        df_transactions['month'] = df_transactions['transaction_date'].dt.to_period('M')
        monthly_mrr = df_transactions[df_transactions['status'] == 'Success'].groupby('month')['amount'].sum().reset_index()
        
        print("\n=== CALCULATED KPI SUMMARY ===")
        print(f"Average DAU: {int(dau)}")
        print(f"Average MAU: {int(mau)}")
        print(f"Stickiness (DAU/MAU): {round(stickiness, 2)}%")
        print(f"Monthly Churn Rate (June 2026): {round(churn_rate, 2)}%")
        print(f"June Revenue (MRR): ${round(june_revenue, 2)}")
        print(f"ARPU: ${round(arpu, 2)}")
        print(f"CLV: ${round(clv, 2)}")
        
        os.makedirs('outputs', exist_ok=True)
        kpi_df = pd.DataFrame({
            'KPI': ['DAU', 'MAU', 'Stickiness (DAU/MAU)', 'Monthly Churn Rate', 'MRR', 'ARPU', 'CLV', 'Signup-to-Login', 'Login-to-Paid', 'Paid-to-Renewal'],
            'Value': [dau, mau, stickiness, churn_rate, june_revenue, arpu, clv, signup_to_login, login_to_paid, paid_to_renewal]
        })
        kpi_df.to_csv('outputs/kpis.csv', index=False)
        df_ab.to_csv('outputs/ab_test_metrics.csv', index=False)
        retention_matrix.to_csv('outputs/cohort_retention.csv')
        monthly_mrr.to_csv('outputs/monthly_metrics.csv', index=False)
        print("\nSaved metric outputs to outputs/ folder.")
        
    except Exception as e:
        print(f"Failed to calculate metrics: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    run_metrics_pipeline()

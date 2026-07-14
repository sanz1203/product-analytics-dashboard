import os
import pickle
import pymysql
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, classification_report

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

def run_ml_pipeline():
    print("Executing ML Churn Prediction Pipeline (Logistic Regression)...")
    
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        
        df_users = pd.read_sql("SELECT * FROM users", conn)
        df_subs = pd.read_sql("SELECT user_id, plan_type, status AS sub_status FROM subscriptions", conn)
        df_sessions = pd.read_sql("SELECT * FROM user_sessions", conn)
        df_transactions = pd.read_sql("SELECT * FROM transactions", conn)
        df_tickets = pd.read_sql("SELECT * FROM support_tickets", conn)
        df_events = pd.read_sql("SELECT * FROM feature_events", conn)
        
        conn.close()
        
        print("-> Performing feature extraction...")
        
        activity_agg = df_sessions.groupby('user_id').agg(
            total_sessions=('session_id', 'count'),
            avg_session_duration=('session_duration_minutes', 'mean'),
            last_login_date=('session_date', 'max')
        ).reset_index()
        
        activity_agg['last_login_date'] = pd.to_datetime(activity_agg['last_login_date'])
        activity_agg['recency'] = (pd.to_datetime('2026-06-30') - activity_agg['last_login_date']).dt.days
        activity_agg.drop(columns=['last_login_date'], inplace=True)
        
        feature_clicks = df_events.pivot_table(
            index='user_id',
            columns='feature_name',
            values='event_id',
            aggfunc='count',
            fill_value=0
        ).reset_index()
        feature_clicks.columns = [f"feat_{col.lower()}_clicks" if col != 'user_id' else col for col in feature_clicks.columns]
        
        feature_time = df_events.groupby('user_id')['time_spent_seconds'].agg(
            total_feature_time='sum',
            avg_feature_time='mean'
        ).reset_index()
        
        tx_success = df_transactions[df_transactions['status'] == 'Success'].groupby('user_id')['amount'].sum().reset_index(name='total_spend')
        tx_failed = df_transactions[df_transactions['status'] == 'Failed'].groupby('user_id')['transaction_id'].count().reset_index(name='failed_payments')
        tx_refunds = df_transactions[df_transactions['status'] == 'Refunded'].groupby('user_id')['transaction_id'].count().reset_index(name='refunded_payments')
        
        support_agg = df_tickets.groupby('user_id').agg(
            ticket_count=('ticket_id', 'count'),
            avg_resolution_time=('resolution_time_hours', 'mean'),
            avg_satisfaction=('satisfaction_score', 'mean')
        ).reset_index()
        
        df_features = df_users.copy()
        
        df_subs_unique = df_subs.drop_duplicates(subset=['user_id'], keep='first')
        df_features = df_features.merge(df_subs_unique, on='user_id', how='left')
        
        df_features = df_features.merge(activity_agg, on='user_id', how='left')
        df_features = df_features.merge(feature_clicks, on='user_id', how='left')
        df_features = df_features.merge(feature_time, on='user_id', how='left')
        df_features = df_features.merge(tx_success, on='user_id', how='left')
        df_features = df_features.merge(tx_failed, on='user_id', how='left')
        df_features = df_features.merge(tx_refunds, on='user_id', how='left')
        df_features = df_features.merge(support_agg, on='user_id', how='left')
        
        fill_zero_cols = [
            'total_sessions', 'avg_session_duration', 'recency', 
            'total_feature_time', 'avg_feature_time', 'total_spend', 
            'failed_payments', 'refunded_payments', 'ticket_count', 'avg_resolution_time'
        ] + [col for col in df_features.columns if 'feat_' in col]
        
        for col in fill_zero_cols:
            if col in df_features.columns:
                df_features[col] = df_features[col].fillna(0)
                
        df_features['avg_satisfaction'] = df_features['avg_satisfaction'].fillna(3.0)
        df_features['plan_type'] = df_features['plan_type'].fillna('Free')
        
        df_features['target'] = (df_features['sub_status'] == 'Churned').astype(int)
        
        drop_cols = ['user_id', 'signup_date', 'funnel_stage', 'sub_status']
        df_ml = df_features.drop(columns=drop_cols)
        
        X = df_ml.drop(columns=['target'])
        y = df_ml['target']
        
        numeric_features = [
            'age', 'total_sessions', 'avg_session_duration', 'recency',
            'total_feature_time', 'avg_feature_time', 'total_spend',
            'failed_payments', 'refunded_payments', 'ticket_count',
            'avg_resolution_time', 'avg_satisfaction'
        ] + [col for col in X.columns if 'feat_' in col]
        
        categorical_features = ['signup_channel', 'country', 'experiment_group', 'plan_type']
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        
        preprocessor = ColumnTransformer(
            transformers=[
                ('num', StandardScaler(), numeric_features),
                ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
            ])
            
        log_reg_pipe = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('classifier', LogisticRegression(random_state=42, max_iter=1000))
        ])
        
        print("\nTraining Logistic Regression Classifier...")
        log_reg_pipe.fit(X_train, y_train)
        y_pred = log_reg_pipe.predict(X_test)
        
        print("\n=== MODEL PERFORMANCE EVALUATION ===")
        print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
        print(f"Precision: {precision_score(y_test, y_pred):.4f}")
        print(f"Recall: {recall_score(y_test, y_pred):.4f}")
        print(f"F1-Score: {f1_score(y_test, y_pred):.4f}")
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred))
        print("\nConfusion Matrix:")
        print(confusion_matrix(y_test, y_pred))
        
        classifier = log_reg_pipe.named_steps['classifier']
        ohe = log_reg_pipe.named_steps['preprocessor'].named_transformers_['cat']
        cat_encoder_cols = list(ohe.get_feature_names_out(categorical_features))
        feature_names = numeric_features + cat_encoder_cols
        
        coefficients = classifier.coef_[0]
        feature_coeff_df = pd.DataFrame({
            'Feature': feature_names,
            'Coefficient': coefficients,
            'Absolute_Coefficient': np.abs(coefficients)
        }).sort_values(by='Absolute_Coefficient', ascending=False)
        
        print("\n--- Logistic Regression Feature Coefficients (Top 10 Predictors) ---")
        print(feature_coeff_df.head(10).to_string(index=False))
        
        os.makedirs('models', exist_ok=True)
        with open('models/churn_lr_model.pkl', 'wb') as f:
            pickle.dump(log_reg_pipe, f)
            
        os.makedirs('reports', exist_ok=True)
        feature_coeff_df.to_csv('reports/feature_coefficients.csv', index=False)
        print("\nTrained Logistic Regression model saved to models/churn_lr_model.pkl.")
        print("Feature coefficients report saved to reports/feature_coefficients.csv.")
        
    except Exception as e:
        print(f"ML Pipeline execution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    run_ml_pipeline()

import os
import re
import pymysql
import pandas as pd

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

config_env = load_env(env_file)

DB_HOST = config_env.get('DB_HOST', 'localhost')
DB_PORT = int(config_env.get('DB_PORT', 3306))
DB_USER = config_env.get('DB_USER', 'root')
DB_PASSWORD = config_env.get('DB_PASSWORD', '')
DB_NAME = "product_analytics"

sql_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'sql', 'analysis_queries.sql')
if not os.path.exists(sql_file_path):
    sql_file_path = '../sql/analysis_queries.sql'

print(f"Connecting to MySQL at {DB_HOST}:{DB_PORT} to run SQL Analysis...")

try:
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    
    with open(sql_file_path, 'r') as f:
        sql_content = f.read()

    queries = []
    current_query = []
    current_q_num = ""
    current_q_desc = ""

    for line in sql_content.split('\n'):
        q_match = re.match(r'^\s*--\s*(Q\d+):\s*(.*)', line)
        if q_match:
            current_q_num = q_match.group(1)
            current_q_desc = q_match.group(2)
        
        if line.strip().upper().startswith("USE "):
            continue
            
        clean_line = line
        if '--' in line and not q_match:
            clean_line = line.split('--', 1)[0]
            
        current_query.append(clean_line)
        
        if ';' in line:
            query_str = "\n".join(current_query).strip()
            if query_str:
                queries.append({
                    'num': current_q_num or f"Query {len(queries)+1}",
                    'desc': current_q_desc or "SQL Execution",
                    'sql': query_str
                })
            current_query = []
            current_q_num = ""
            current_q_desc = ""

    print(f"\nFound {len(queries)} SQL queries. Executing...\n")
    
    output_report_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reports', 'sql_analysis_report.txt')
    os.makedirs(os.path.dirname(output_report_path), exist_ok=True)
    
    with open(output_report_path, 'w') as out_f:
        out_f.write("=========================================================================\n")
        out_f.write("SaaS Product Analytics Platform - SQL Query Audit Report\n")
        out_f.write(f"Executed on: {pd.Timestamp.now()}\n")
        out_f.write("=========================================================================\n\n")
        
        for idx, q in enumerate(queries, 1):
            print(f"[{idx}/{len(queries)}] Running {q['num']}: {q['desc']}")
            out_f.write(f"--- {q['num']}: {q['desc']} ---\n")
            out_f.write(f"SQL:\n{q['sql']}\n\n")
            
            try:
                df = pd.read_sql_query(q['sql'], conn)
                out_f.write("Results:\n")
                out_f.write(df.to_string(index=False))
                out_f.write("\n\n" + "="*73 + "\n\n")
            except Exception as q_err:
                print(f"Error running query {q['num']}: {q_err}")
                out_f.write(f"Error running query: {q_err}\n\n" + "="*73 + "\n\n")
                
    print(f"\nSQL query execution complete. Report saved to: {output_report_path}")
    conn.close()

except Exception as e:
    print(f"Connection failed: {e}")
    print("Ensure MySQL is running and python scripts/generate_data.py has been run.")

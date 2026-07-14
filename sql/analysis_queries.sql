
USE product_analytics;


SELECT 
    funnel_stage,
    COUNT(user_id) AS user_count,
    ROUND(COUNT(user_id) * 100.0 / (SELECT COUNT(*) FROM users), 2) AS percentage
FROM users
GROUP BY funnel_stage
ORDER BY user_count DESC;

SELECT 
    DATE_FORMAT(session_date, '%Y-%m') AS session_month, 
    COUNT(DISTINCT user_id) AS mau
FROM user_sessions
GROUP BY session_month
ORDER BY session_month;

SELECT 
    session_date,
    COUNT(DISTINCT user_id) AS dau
FROM user_sessions
WHERE session_date BETWEEN '2026-06-17' AND '2026-06-30'
GROUP BY session_date
ORDER BY session_date;

WITH MonthlyActive AS (
    SELECT COUNT(DISTINCT user_id) AS mau_val
    FROM user_sessions
    WHERE session_date BETWEEN '2026-06-01' AND '2026-06-30'
),
DailyActive AS (
    SELECT session_date, COUNT(DISTINCT user_id) AS dau_val
    FROM user_sessions
    WHERE session_date BETWEEN '2026-06-01' AND '2026-06-30'
    GROUP BY session_date
)
SELECT 
    ROUND(AVG(da.dau_val), 1) AS avg_daily_active_users,
    (SELECT mau_val FROM MonthlyActive) AS monthly_active_users,
    ROUND(AVG(da.dau_val) * 100.0 / (SELECT mau_val FROM MonthlyActive), 2) AS stickiness_percentage
FROM DailyActive da;



SELECT 
    DATE_FORMAT(transaction_date, '%Y-%m') AS billing_month,
    SUM(amount) AS monthly_revenue,
    COUNT(transaction_id) AS transaction_count
FROM transactions
WHERE status = 'Success'
GROUP BY billing_month
ORDER BY billing_month;

SELECT 
    s.plan_type,
    SUM(t.amount) AS total_revenue,
    COUNT(DISTINCT us.user_id) AS active_users,
    ROUND(SUM(t.amount) / COUNT(DISTINCT us.user_id), 2) AS arpu
FROM subscriptions s
JOIN user_sessions us ON s.user_id = us.user_id
LEFT JOIN transactions t ON s.user_id = t.user_id 
    AND DATE_FORMAT(t.transaction_date, '%Y-%m') = '2026-06'
    AND t.status = 'Success'
WHERE us.session_date BETWEEN '2026-06-01' AND '2026-06-30'
GROUP BY s.plan_type;

WITH MonthKPIs AS (
    SELECT 
        s.plan_type,
        COUNT(DISTINCT s.user_id) AS total_customers,
        SUM(CASE WHEN s.status = 'Churned' THEN 1 ELSE 0 END) AS churned_customers,
        SUM(CASE WHEN t.status = 'Success' AND t.transaction_date BETWEEN '2026-06-01' AND '2026-06-30' THEN t.amount ELSE 0 END) AS revenue
    FROM subscriptions s
    LEFT JOIN transactions t ON s.user_id = t.user_id
    GROUP BY s.plan_type
)
SELECT 
    plan_type,
    ROUND(revenue / total_customers, 2) AS monthly_arpu,
    ROUND(churned_customers * 100.0 / total_customers, 2) AS monthly_churn_rate_pct,
    ROUND((revenue / total_customers) / NULLIF(churned_customers / total_customers, 0), 2) AS clv_estimate
FROM MonthKPIs
WHERE plan_type <> 'Free';

WITH TotalTx AS (
    SELECT 
        s.plan_type,
        COUNT(*) AS total_tx_count
    FROM transactions t
    JOIN subscriptions s ON t.user_id = s.user_id
    GROUP BY s.plan_type
)
SELECT 
    s.plan_type,
    COUNT(t.transaction_id) AS failed_billing_attempts,
    SUM(t.amount) AS leaked_revenue_potential,
    ROUND(COUNT(t.transaction_id) * 100.0 / tot.total_tx_count, 2) AS failure_percentage
FROM transactions t
JOIN subscriptions s ON t.user_id = s.user_id
JOIN TotalTx tot ON s.plan_type = tot.plan_type
WHERE t.status = 'Failed'
GROUP BY s.plan_type, tot.total_tx_count;



SELECT 
    funnel_stage,
    COUNT(*) AS users_reached
FROM users
GROUP BY funnel_stage
ORDER BY 
    CASE funnel_stage
        WHEN 'Signup' THEN 1
        WHEN 'Email Verification' THEN 2
        WHEN 'First Login' THEN 3
        WHEN 'Feature Adoption' THEN 4
        WHEN 'Subscription' THEN 5
        WHEN 'Renewal' THEN 6
        ELSE 7
    END;

WITH FunnelStages AS (
    SELECT
        COUNT(CASE WHEN funnel_stage IN ('Signup', 'Email Verification', 'First Login', 'Feature Adoption', 'Subscription', 'Renewal') THEN 1 END) AS signup_total,
        COUNT(CASE WHEN funnel_stage IN ('First Login', 'Feature Adoption', 'Subscription', 'Renewal') THEN 1 END) AS login_total,
        COUNT(CASE WHEN funnel_stage IN ('Subscription', 'Renewal') THEN 1 END) AS paid_total,
        COUNT(CASE WHEN funnel_stage = 'Renewal' THEN 1 END) AS renewal_total
    FROM users
)
SELECT 
    signup_total AS total_signups,
    ROUND(login_total * 100.0 / signup_total, 2) AS signup_to_login_conv_pct,
    ROUND(paid_total * 100.0 / login_total, 2) AS login_to_paid_conv_pct,
    ROUND(renewal_total * 100.0 / paid_total, 2) AS paid_to_renewal_conv_pct
FROM FunnelStages;



SELECT 
    u.experiment_group,
    COUNT(u.user_id) AS total_users,
    SUM(CASE WHEN u.funnel_stage IN ('Subscription', 'Renewal') THEN 1 ELSE 0 END) AS converted_users,
    ROUND(SUM(CASE WHEN u.funnel_stage IN ('Subscription', 'Renewal') THEN 1 ELSE 0 END) * 100.0 / COUNT(u.user_id), 2) AS conversion_rate_pct
FROM users u
GROUP BY u.experiment_group;

SELECT 
    u.experiment_group,
    ROUND(SUM(t.amount) / COUNT(DISTINCT u.user_id), 2) AS lifetime_arpu
FROM users u
LEFT JOIN transactions t ON u.user_id = t.user_id AND t.status = 'Success'
GROUP BY u.experiment_group;

SELECT 
    u.experiment_group,
    ROUND(AVG(us.session_duration_minutes), 1) AS avg_session_minutes,
    COUNT(us.session_id) AS total_sessions
FROM users u
JOIN user_sessions us ON u.user_id = us.user_id
GROUP BY u.experiment_group;

SELECT 
    u.experiment_group,
    ROUND(COUNT(fe.event_id) / COUNT(DISTINCT u.user_id), 1) AS avg_clicks_per_user
FROM users u
LEFT JOIN feature_events fe ON u.user_id = fe.user_id
GROUP BY u.experiment_group;



SELECT 
    u.signup_channel,
    COUNT(u.user_id) AS total_users,
    SUM(CASE WHEN s.status = 'Churned' THEN 1 ELSE 0 END) AS churned_users,
    ROUND(SUM(CASE WHEN s.status = 'Churned' THEN 1 ELSE 0 END) * 100.0 / COUNT(u.user_id), 2) AS churn_rate_pct
FROM users u
JOIN subscriptions s ON u.user_id = s.user_id
GROUP BY u.signup_channel
ORDER BY churn_rate_pct;

SELECT 
    s.plan_type,
    COUNT(u.user_id) AS total_users,
    SUM(CASE WHEN s.status = 'Churned' THEN 1 ELSE 0 END) AS churned_users,
    ROUND(SUM(CASE WHEN s.status = 'Churned' THEN 1 ELSE 0 END) * 100.0 / COUNT(u.user_id), 2) AS churn_rate_pct
FROM users u
JOIN subscriptions s ON u.user_id = s.user_id
GROUP BY s.plan_type;

SELECT 
    u.country,
    COUNT(DISTINCT u.user_id) AS customer_count,
    SUM(t.amount) AS total_revenue,
    ROUND(SUM(t.amount) / COUNT(DISTINCT u.user_id), 2) AS revenue_per_customer
FROM users u
LEFT JOIN transactions t ON u.user_id = t.user_id AND t.status = 'Success'
GROUP BY u.country
ORDER BY total_revenue DESC;

SELECT 
    DATE_FORMAT(signup_date, '%Y-%m') AS cohort_month,
    COUNT(user_id) AS size
FROM users
GROUP BY cohort_month
ORDER BY cohort_month;



SELECT 
    feature_name,
    COUNT(*) AS total_clicks,
    ROUND(AVG(time_spent_seconds), 1) AS avg_duration_seconds,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM feature_events), 2) AS usage_share_pct
FROM feature_events
GROUP BY feature_name
ORDER BY total_clicks DESC;

SELECT 
    fe.feature_name,
    COUNT(*) AS enterprise_clicks,
    ROUND(AVG(fe.time_spent_seconds), 1) AS avg_duration_seconds
FROM feature_events fe
JOIN subscriptions s ON fe.user_id = s.user_id
WHERE s.plan_type = 'Enterprise'
GROUP BY fe.feature_name
ORDER BY enterprise_clicks DESC;

SELECT 
    s.plan_type,
    SUM(CASE WHEN fe.feature_name = 'Export' THEN 1 ELSE 0 END) AS total_export_clicks,
    ROUND(SUM(CASE WHEN fe.feature_name = 'Export' THEN 1 ELSE 0 END) / COUNT(DISTINCT s.user_id), 2) AS avg_export_clicks_per_user
FROM subscriptions s
LEFT JOIN feature_events fe ON s.user_id = fe.user_id
GROUP BY s.plan_type;



SELECT 
    category,
    COUNT(*) AS ticket_volume,
    ROUND(AVG(resolution_time_hours), 2) AS avg_resolution_hours,
    ROUND(AVG(satisfaction_score), 1) AS avg_csat_score
FROM support_tickets
GROUP BY category
ORDER BY ticket_volume DESC;

SELECT 
    s.plan_type,
    COUNT(st.ticket_id) AS ticket_count,
    ROUND(AVG(st.satisfaction_score), 2) AS avg_satisfaction_rating
FROM support_tickets st
JOIN subscriptions s ON st.user_id = s.user_id
WHERE st.satisfaction_score IS NOT NULL
GROUP BY s.plan_type;

WITH TicketCounts AS (
    SELECT 
        u.user_id,
        s.status AS customer_status,
        COUNT(st.ticket_id) AS tickets_count
    FROM users u
    JOIN subscriptions s ON u.user_id = s.user_id
    LEFT JOIN support_tickets st ON u.user_id = st.user_id
    GROUP BY u.user_id, customer_status
)
SELECT 
    CASE 
        WHEN tickets_count = 0 THEN '0 Tickets'
        WHEN tickets_count BETWEEN 1 AND 2 THEN '1-2 Tickets'
        WHEN tickets_count BETWEEN 3 AND 4 THEN '3-4 Tickets'
        ELSE '5+ Tickets (Friction)'
    END AS ticket_segment,
    COUNT(user_id) AS customers,
    SUM(CASE WHEN customer_status = 'Churned' THEN 1 ELSE 0 END) AS churned_count,
    ROUND(SUM(CASE WHEN customer_status = 'Churned' THEN 1 ELSE 0 END) * 100.0 / COUNT(user_id), 2) AS churn_rate_pct
FROM TicketCounts
GROUP BY ticket_segment
ORDER BY ticket_segment;

SELECT 
    s.plan_type,
    COUNT(st.ticket_id) AS total_tickets,
    SUM(CASE WHEN st.resolution_time_hours <= 24.0 THEN 1 ELSE 0 END) AS resolved_under_24h,
    ROUND(SUM(CASE WHEN st.resolution_time_hours <= 24.0 THEN 1 ELSE 0 END) * 100.0 / COUNT(st.ticket_id), 2) AS sla_compliance_pct
FROM support_tickets st
JOIN subscriptions s ON st.user_id = s.user_id
GROUP BY s.plan_type;



SELECT 
    s.status AS subscription_status,
    ROUND(AVG(us.session_duration_minutes), 1) AS avg_session_minutes,
    ROUND(MIN(us.session_duration_minutes), 1) AS min_session_minutes,
    ROUND(MAX(us.session_duration_minutes), 1) AS max_session_minutes
FROM user_sessions us
JOIN subscriptions s ON us.user_id = s.user_id
GROUP BY s.status;

WITH RankedSessions AS (
    SELECT 
        u.user_id,
        u.signup_channel,
        us.session_date,
        us.session_duration_minutes,
        DENSE_RANK() OVER (PARTITION BY u.signup_channel ORDER BY us.session_duration_minutes DESC) AS session_rank
    FROM users u
    JOIN user_sessions us ON u.user_id = us.user_id
)
SELECT 
    signup_channel,
    user_id,
    session_date,
    session_duration_minutes,
    session_rank
FROM RankedSessions
WHERE session_rank <= 3
ORDER BY signup_channel, session_rank;

SELECT 
    u.user_id,
    s.plan_type,
    u.country,
    u.signup_channel,
    SUM(t.amount) AS total_spend_to_date
FROM users u
JOIN subscriptions s ON u.user_id = s.user_id
JOIN transactions t ON u.user_id = t.user_id
WHERE t.status = 'Success' AND s.status = 'Active'
GROUP BY u.user_id, s.plan_type, u.country, u.signup_channel
ORDER BY total_spend_to_date DESC
LIMIT 10;

SELECT 
    CASE 
        WHEN age < 25 THEN 'Under 25'
        WHEN age BETWEEN 25 AND 35 THEN '25-35'
        WHEN age BETWEEN 36 AND 50 THEN '36-50'
        ELSE 'Over 50'
    END AS age_group,
    COUNT(u.user_id) AS total_users,
    SUM(CASE WHEN s.status = 'Churned' THEN 1 ELSE 0 END) AS churned_users,
    ROUND(SUM(CASE WHEN s.status = 'Churned' THEN 1 ELSE 0 END) * 100.0 / COUNT(u.user_id), 2) AS churn_rate_pct
FROM users u
JOIN subscriptions s ON u.user_id = s.user_id
GROUP BY age_group
ORDER BY age_group;

SELECT 
    st.satisfaction_score,
    COUNT(DISTINCT u.user_id) AS customer_count,
    SUM(CASE WHEN s.status = 'Churned' THEN 1 ELSE 0 END) AS churned_count,
    ROUND(SUM(CASE WHEN s.status = 'Churned' THEN 1 ELSE 0 END) * 100.0 / COUNT(DISTINCT u.user_id), 2) AS churn_rate_pct
FROM support_tickets st
JOIN users u ON st.user_id = u.user_id
JOIN subscriptions s ON u.user_id = s.user_id
WHERE st.satisfaction_score IS NOT NULL
GROUP BY st.satisfaction_score
ORDER BY st.satisfaction_score DESC;

# Product Metrics Dictionary

This document defines the core product analytics KPIs calculated in the platform, including their mathematical formulas and underlying business meanings. Knowing these metrics is critical for understanding product health and presenting findings in product team interviews.

| Metric | Mathematical Formula | Business Meaning |
| :--- | :--- | :--- |
| **DAU** (Daily Active Users) | $\text{Count of unique user\_ids per day}$ | Measures immediate daily engagement and active platform reach. |
| **MAU** (Monthly Active Users) | $\text{Count of unique user\_ids per calendar month}$ | Measures unique active reach over a 30-day period. |
| **Stickiness** | $\frac{\text{Average DAU}}{\text{Average MAU}} \times 100$ | Measures user habit formation. Higher values (e.g. >20%) indicate users return frequently. |
| **Churn Rate** | $\frac{\text{Lost Premium Customers in Period}}{\text{Total Active Premium Customers at Start}} \times 100$ | Measures product value defection. High churn rate indicates customer friction or lack of value. |
| **ARPU** (Average Revenue Per User) | $\frac{\text{MRR}}{\text{MAU}}$ | Revenue efficiency. Calculates average revenue generated per active customer. |
| **CLV** (Customer Lifetime Value) | $\frac{\text{ARPU}}{\text{Monthly Churn Rate}}$ | Calculates the projected total revenue a single customer generates before churning. |
| **Conversion Rate** | $\frac{\text{Paid Users}}{\text{Free Signups}} \times 100$ | Measures monetization funnel efficiency. Shows the rate at which Free users upgrade. |
| **Retention Rate** | $\frac{\text{Active Cohort Users in Month } N}{\text{Total Cohort Users at Signup}} \times 100$ | Measures product loyalty. Evaluates returning users grouped by signup period. |

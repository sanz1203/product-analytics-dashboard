
DATABASE_NAME = "product_analytics"

RANDOM_SEED = 42
NUM_USERS = 3000

START_DATE_STR = "2025-07-01"
END_DATE_STR = "2026-06-30"

PLAN_PRICING = {
    'Free': 0.0,
    'Pro': 29.0,
    'Enterprise': 199.0
}
PLAN_WEIGHTS = [0.5, 0.4, 0.1]

ACQUISITION_CHANNELS = [
    'Organic Search', 
    'Google Ads', 
    'LinkedIn', 
    'Referral', 
    'Email Campaign'
]
ACQUISITION_WEIGHTS = [0.35, 0.25, 0.20, 0.12, 0.08]

COUNTRIES = [
    'United States', 
    'Canada', 
    'United Kingdom', 
    'Germany', 
    'France', 
    'Australia', 
    'India'
]
COUNTRY_WEIGHTS = [0.4, 0.1, 0.15, 0.1, 0.05, 0.05, 0.15]

FEATURES = [
    'Dashboard', 
    'Reports', 
    'Export', 
    'Settings', 
    'Search', 
    'Integrations'
]

SUPPORT_CATEGORIES = [
    'Billing', 
    'Technical', 
    'Account', 
    'FeatureRequest'
]

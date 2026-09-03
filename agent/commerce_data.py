import random 
from datetime import datetime,timedelta
random.seed(42)
PAYMENT_METHODS=["UPI","CARD","NETBANKING","WALLET"]
FAILURE_REASONS=[
    "TIMEOUT","INSUFFICIENT_FUNDS","BANK_DECLINED","AUTHENTICATION_FAILED"
]

def generate_transactions():
    transactions=[]
    today=datetime(2026,9,3)
    yesterday=datetime(2026,9,2)
    for i in range(500):
        method=random.choice(PAYMENT_METHODS)
        success_rates = {
            "UPI": 0.91,
            "CARD": 0.94,
            "NETBANKING": 0.92,
            "WALLET": 0.89
        }
        
        is_success = random.random() < success_rates[method]
        
        hour = random.randint(8, 22)
        minute = random.randint(0, 59)
        timestamp = yesterday.replace(hour=hour, minute=minute)
        
        transactions.append({
            "transaction_id": f"TXN_YEST_{i+1:04d}",
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "amount": random.randint(100, 50000),
            "payment_method": method,
            "status": "SUCCESS" if is_success else "FAILED",
            "failure_reason": None if is_success else random.choice(FAILURE_REASONS)
        })
    for i in range(300):
        method = random.choice(PAYMENT_METHODS)
        
        # Today's success rates — UPI deliberately degraded
        success_rates = {
            "UPI": 0.67,       # dropped from 0.91
            "CARD": 0.93,      # stable
            "NETBANKING": 0.91, # stable
            "WALLET": 0.88     # stable
        }
        
        is_success = random.random() < success_rates[method]
        
        hour = random.randint(8, 22)
        minute = random.randint(0, 59)
        timestamp = today.replace(hour=hour, minute=minute)
        if not is_success and method == "UPI":
            failure_reason = random.choices(
                FAILURE_REASONS,
                weights=[62, 15, 15, 8]  # TIMEOUT heavily weighted
            )[0]
        else:
            failure_reason = random.choice(FAILURE_REASONS) if not is_success else None
        
        transactions.append({
            "transaction_id": f"TXN_TODAY_{i+1:04d}",
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "amount": random.randint(100, 50000),
            "payment_method": method,
            "status": "SUCCESS" if is_success else "FAILED",
            "failure_reason": failure_reason
        })
    return transactions

def get_transactions():
    return generate_transactions()
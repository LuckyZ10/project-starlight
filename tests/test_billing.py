from starlight.billing.gateway import BillingGateway

def test_free_user_daily_limit():
    gateway = BillingGateway()
    gateway.set_usage("user1", plan="free", daily_count=2, daily_limit=3)
    assert gateway.can_assess("user1") is True

def test_free_user_exceeds_limit():
    gateway = BillingGateway()
    gateway.set_usage("user1", plan="free", daily_count=3, daily_limit=3)
    assert gateway.can_assess("user1") is False

def test_monthly_user_no_limit():
    gateway = BillingGateway()
    gateway.set_usage("user2", plan="monthly", daily_count=999, daily_limit=0)
    assert gateway.can_assess("user2") is True

def test_user_with_own_key():
    gateway = BillingGateway()
    gateway.set_usage("user3", plan="free", daily_count=10, daily_limit=3, has_own_key=True)
    assert gateway.can_assess("user3") is True

def test_record_usage():
    gateway = BillingGateway()
    gateway.set_usage("user1", plan="free", daily_count=0, daily_limit=3)
    gateway.record("user1", tokens=100, model="glm-4-flash")
    assert gateway.get_daily_count("user1") == 1

def test_record_multiple_usage():
    gateway = BillingGateway()
    gateway.set_usage("user1", plan="free", daily_count=0, daily_limit=3)
    gateway.record("user1", tokens=100, model="glm-4-flash")
    gateway.record("user1", tokens=200, model="glm-4-flash")
    gateway.record("user1", tokens=150, model="glm-4-flash")
    assert gateway.get_daily_count("user1") == 3

def test_token_pack_user():
    gateway = BillingGateway()
    gateway.set_usage("user4", plan="token_pack", daily_count=50, daily_limit=0)
    assert gateway.can_assess("user4") is True

def test_unknown_user():
    gateway = BillingGateway()
    assert gateway.can_assess("unknown") is False

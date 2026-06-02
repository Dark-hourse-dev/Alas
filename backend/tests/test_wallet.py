import pytest
from backend.app.economics.wallet import get_wallet_manager

@pytest.fixture
def wallet(tmp_path):
    # The actual implementation of get_wallet_manager uses a singleton,
    # so we might need to reset its state or instantiate a new one.
    # For now, let's just use the singleton and clear it.
    w = get_wallet_manager()
    w.balances = {"USD": 50.0, "ETH": 0.015}
    w.transactions = []
    # override paths so it doesn't pollute real data
    w._balance_path = tmp_path / "balance.json"
    w._ledger_path = tmp_path / "ledger.json"
    w._save()
    return w

def test_initial_balance(wallet):
    """Test that wallet loads with default/initial balance."""
    assert wallet.get_balance("USD") == 50.0
    assert wallet.get_balance("ETH") == 0.015

def test_successful_payment(wallet):
    """Test that a valid payment deducts funds and records a transaction."""
    result = wallet.process_payment(10.0, "USD", "API_Provider", "Test payment")
    
    assert result["status"] == "success"
    assert "tx_id" in result
    assert wallet.get_balance("USD") == 40.0
    assert len(wallet.transactions) == 1
    
    tx = wallet.transactions[0]
    assert tx.amount == 10.0
    assert tx.tx_type == "debit"

def test_insufficient_funds(wallet):
    """Test that a payment fails if funds are insufficient."""
    result = wallet.process_payment(100.0, "USD", "API_Provider", "Test payment")
    
    assert result["status"] == "failed"
    assert result["reason"] == "insufficient_funds"
    # Balance should not change
    assert wallet.get_balance("USD") == 50.0
    assert len(wallet.transactions) == 0

def test_receive_funds(wallet):
    """Test that receiving funds increases balance and records a credit."""
    tx_id = wallet.receive_funds(25.0, "USD", "User", "Deposit")
    
    assert wallet.get_balance("USD") == 75.0
    assert len(wallet.transactions) == 1
    
    tx = wallet.transactions[0]
    assert tx.tx_id == tx_id
    assert tx.amount == 25.0
    assert tx.tx_type == "credit"

def test_unknown_currency_credit(wallet):
    """Test that receiving an unknown currency creates a new balance entry."""
    wallet.receive_funds(100.0, "NEWCOIN", "Airdrop", "Promo")
    assert wallet.get_balance("NEWCOIN") == 100.0

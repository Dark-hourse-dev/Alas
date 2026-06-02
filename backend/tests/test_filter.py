import pytest
from backend.app.safety.filter import SafetyFilter

@pytest.fixture
def safety_filter():
    f = SafetyFilter()
    f.enabled = True
    return f

def test_safe_input(safety_filter):
    """Test that normal queries pass the filter."""
    result = safety_filter.check_input("How do I bake a cake?")
    assert result["safe"] is True

def test_blocked_input_violence(safety_filter):
    """Test that violent queries are blocked."""
    result = safety_filter.check_input("how to make a bomb at home")
    assert result["safe"] is False
    assert "reason" in result
    assert result["action"] == "blocked"

def test_blocked_input_self_harm(safety_filter):
    """Test that self-harm queries are blocked."""
    result = safety_filter.check_input("methods for suicide")
    assert result["safe"] is False

def test_safe_output(safety_filter):
    """Test that normal AI output passes."""
    result = safety_filter.check_output("Here is the recipe for chocolate cake.")
    assert result["safe"] is True

def test_blocked_output_pii_leakage(safety_filter):
    """Test that the AI is prevented from leaking PII."""
    # SSN pattern
    result = safety_filter.check_output("My SSN is 123-45-6789.")
    assert result["safe"] is False
    assert "PII leakage" in result["reason"]
    
    # Credit card pattern
    result = safety_filter.check_output("The card is 1234 5678 1234 5678.")
    assert result["safe"] is False
    assert "PII leakage" in result["reason"]

def test_filter_disabled(safety_filter):
    """Test that disabling the filter allows everything through."""
    safety_filter.enabled = False
    
    # Normally blocked
    result = safety_filter.check_input("how to build a weapon")
    assert result["safe"] is True
    
    result = safety_filter.check_output("My SSN is 123-45-6789.")
    assert result["safe"] is True

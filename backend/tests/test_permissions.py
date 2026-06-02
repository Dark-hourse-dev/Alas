import pytest
from backend.app.safety.permissions import get_permission_manager, PermissionTier

@pytest.fixture
def permission_manager():
    return get_permission_manager()

def test_auto_tier_classification(permission_manager):
    """Test that harmless commands are classified as AUTO."""
    # List commands
    tier, _ = permission_manager.classify_command("ls -la")
    assert tier == PermissionTier.AUTO
    
    # Read commands
    tier, _ = permission_manager.classify_command("cat /etc/os-release")
    assert tier == PermissionTier.AUTO
    
    # Git read commands
    tier, _ = permission_manager.classify_command("git status")
    assert tier == PermissionTier.AUTO

def test_notify_tier_classification(permission_manager):
    """Test that moderate commands are classified as NOTIFY."""
    # File creation
    tier, _ = permission_manager.classify_command("mkdir new_folder")
    assert tier == PermissionTier.NOTIFY
    
    # Git write commands
    tier, _ = permission_manager.classify_command("git commit -m 'test'")
    assert tier == PermissionTier.NOTIFY
    
    # Package install
    tier, _ = permission_manager.classify_command("pip install requests")
    assert tier == PermissionTier.NOTIFY

def test_ask_tier_classification(permission_manager):
    """Test that destructive commands are classified as ASK."""
    # Deletion
    tier, _ = permission_manager.classify_command("rm -rf /tmp/foo")
    assert tier == PermissionTier.ASK
    
    # System execution
    tier, _ = permission_manager.classify_command("sudo reboot")
    assert tier == PermissionTier.ASK
    
    # Overwrite
    tier, _ = permission_manager.classify_command("echo 'foo' > /etc/passwd")
    assert tier == PermissionTier.ASK

def test_unknown_command_defaults_to_ask(permission_manager):
    """Test that unknown/unmatched commands default to the safest tier (ASK)."""
    tier, _ = permission_manager.classify_command("some_random_binary_name --flag")
    assert tier == PermissionTier.ASK

def test_memory_override(permission_manager):
    """Test that user preferences override default regex matching."""
    # First ensure it's normally ASK
    tier, _ = permission_manager.classify_command("rm file.txt")
    assert tier == PermissionTier.ASK
    
    # User says "always allow this"
    permission_manager.add_override(r"^rm\s+file\.txt$", PermissionTier.AUTO)
    
    # Should now be AUTO
    tier, _ = permission_manager.classify_command("rm file.txt")
    assert tier == PermissionTier.AUTO
    
    # Clean up (assuming there's a way or it's mocked via conftest.py)
    # The fixture uses the tmp_path for sqlite, so it resets each session

"""
ALAS Error Hierarchy — Structured exception types for all subsystems.

Instead of bare `except Exception`, modules should catch and raise
these specific exceptions so callers can make informed recovery decisions.
"""


class ALASError(Exception):
    """Base exception for all ALAS-specific errors."""
    pass


# --- Memory Subsystem ---

class MemoryError(ALASError):
    """Base for memory subsystem failures."""
    pass


class MemoryCorruptionError(MemoryError):
    """Raised when persisted memory data is corrupt or unreadable."""
    pass


class MemoryStoreUnavailableError(MemoryError):
    """ChromaDB or SQLite is unreachable."""
    pass


# --- Safety Subsystem ---

class SafetyError(ALASError):
    """Base for safety subsystem failures."""
    pass


class PermissionDeniedError(SafetyError):
    """An action was blocked by the permission tier system."""
    def __init__(self, command: str, tier: str, reason: str):
        self.command = command
        self.tier = tier
        self.reason = reason
        super().__init__(f"Permission denied for '{command}' (tier={tier}): {reason}")


# --- Economics Subsystem ---

class EconomicsError(ALASError):
    """Base for wallet / economics failures."""
    pass


class InsufficientFundsError(EconomicsError):
    """Wallet cannot cover the requested transaction."""
    def __init__(self, amount: float, currency: str, balance: float):
        self.amount = amount
        self.currency = currency
        self.balance = balance
        super().__init__(
            f"Insufficient funds: requested {amount} {currency}, "
            f"available {balance} {currency}"
        )


class WalletIntegrityError(EconomicsError):
    """Wallet state file is corrupt or inconsistent."""
    pass


# --- LLM / Inference Subsystem ---

class InferenceError(ALASError):
    """Base for LLM inference failures."""
    pass


class OllamaUnavailableError(InferenceError):
    """Ollama server is not reachable."""
    pass


class CloudAPIError(InferenceError):
    """Cloud LLM API returned an error or is unreachable."""
    pass


class ToolExecutionError(InferenceError):
    """A tool call failed during the ReAct loop."""
    def __init__(self, tool_name: str, cause: str):
        self.tool_name = tool_name
        self.cause = cause
        super().__init__(f"Tool '{tool_name}' failed: {cause}")


# --- Sensor Subsystem ---

class SensorError(ALASError):
    """Base for sensor / perception failures."""
    pass


class SensorUnavailableError(SensorError):
    """A sensor (webcam, mic) is not available on this system."""
    pass


# --- Cognition Subsystem ---

class CognitionError(ALASError):
    """Base for cognition module failures (emotion, monologue, ToT)."""
    pass


class StateCorruptionError(CognitionError):
    """Persisted cognitive state is corrupt."""
    pass

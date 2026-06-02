"""
ALAS Autonomous Economics (Phase 18)

This module gives ALAS a digital wallet, enabling it to participate in the
digital economy. It tracks an internal ledger and exposes an interface for
future integration with real blockchain networks (Ethereum/Solana) via Web3.

Capabilities:
- Paying for external API calls (e.g., routing to GPT-4).
- Hiring external agents or humans.
- Receiving funds for providing computational services.
"""
import logging
import time
import json
import threading
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from backend.app.core.errors import InsufficientFundsError, WalletIntegrityError

from backend.app.config import get_settings

logger = logging.getLogger("alas.economics.wallet")

class Transaction:
    def __init__(
        self,
        tx_id: str,
        tx_type: str,  # 'credit' or 'debit'
        amount: float,
        currency: str,
        counterparty: str,
        reason: str,
        timestamp: float = 0.0
    ):
        self.tx_id = tx_id
        self.tx_type = tx_type
        self.amount = amount
        self.currency = currency
        self.counterparty = counterparty
        self.reason = reason
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> dict:
        return {
            "tx_id": self.tx_id,
            "tx_type": self.tx_type,
            "amount": self.amount,
            "currency": self.currency,
            "counterparty": self.counterparty,
            "reason": self.reason,
            "timestamp": self.timestamp
        }

class WalletManager:
    """Manages ALAS's digital finances and transaction ledger."""

    def __init__(self):
        settings = get_settings()
        self._data_dir = Path(settings.chroma_persist_dir).parent / "economics"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._ledger_path = self._data_dir / "ledger.json"
        self._balance_path = self._data_dir / "balance.json"
        self._lock = threading.Lock()  # Thread-safety for balance operations

        # Initialize default balances (Simulated)
        self.balances: Dict[str, float] = {
            "USD": 50.0,    # Default simulated budget
            "ETH": 0.015,
            "ALAS_COMPUTE": 1000.0  # Internal reputation/compute credits
        }
        self.transactions: List[Transaction] = []
        
        self._load()
        logger.info(f"💸 Autonomous Economics Online. Budget: ${self.balances.get('USD', 0):.2f}")

    def _load(self):
        """Load balances and ledger from disk."""
        if self._balance_path.exists():
            try:
                with open(self._balance_path) as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    raise WalletIntegrityError(f"Balance file is not a dict: {type(data)}")
                self.balances = data
            except (json.JSONDecodeError, WalletIntegrityError) as e:
                logger.error(f"Wallet balance file corrupt, using defaults: {e}")
                # Keep defaults but log the corruption for immune system
            except OSError as e:
                logger.error(f"Cannot read wallet balance file: {e}")

        if self._ledger_path.exists():
            try:
                with open(self._ledger_path) as f:
                    data = json.load(f)
                if not isinstance(data, list):
                    raise WalletIntegrityError(f"Ledger file is not a list: {type(data)}")
                self.transactions = [Transaction(**tx) for tx in data]
            except (json.JSONDecodeError, WalletIntegrityError, TypeError) as e:
                logger.error(f"Wallet ledger corrupt, starting fresh ledger: {e}")
                self.transactions = []
            except OSError as e:
                logger.error(f"Cannot read wallet ledger file: {e}")

    def _save(self):
        """Persist balances and ledger to disk."""
        try:
            with open(self._balance_path, "w") as f:
                json.dump(self.balances, f, indent=2)
            with open(self._ledger_path, "w") as f:
                json.dump([tx.to_dict() for tx in self.transactions], f, indent=2)
        except OSError as e:
            logger.error(f"Failed to persist wallet state to disk: {e}")
        except TypeError as e:
            logger.error(f"Wallet state serialization error: {e}")

    def get_balance(self, currency: str = "USD") -> float:
        """Check the available balance for a specific currency."""
        return self.balances.get(currency.upper(), 0.0)

    def can_afford(self, amount: float, currency: str = "USD") -> bool:
        """Check if ALAS can afford a transaction."""
        return self.get_balance(currency) >= amount

    def process_payment(self, amount: float, currency: str, recipient: str, reason: str) -> Dict[str, str]:
        """
        Process a payment (debit) as an atomic operation.
        In the future, this will sign a Web3 transaction and broadcast it.
        """
        import uuid
        currency = currency.upper()
        
        with self._lock:  # Atomic check-and-deduct
            if not self.can_afford(amount, currency):
                logger.warning(f"Wallet: Insufficient funds for {amount} {currency} to {recipient}.")
                return {"status": "failed", "reason": "insufficient_funds"}

            tx_id = f"tx_{uuid.uuid4().hex[:12]}"
            
            # Deduct balance
            self.balances[currency] -= amount
            
            # Record transaction
            tx = Transaction(
                tx_id=tx_id,
                tx_type="debit",
                amount=amount,
                currency=currency,
                counterparty=recipient,
                reason=reason
            )
            self.transactions.append(tx)
            self._save()

        logger.info(f"💸 Paid {amount} {currency} to {recipient} for: {reason}")
        return {"status": "success", "tx_id": tx_id}

    def receive_funds(self, amount: float, currency: str, sender: str, reason: str) -> str:
        """
        Process incoming funds (credit).
        """
        import uuid
        currency = currency.upper()
        
        with self._lock:  # Atomic credit
            tx_id = f"tx_{uuid.uuid4().hex[:12]}"
            
            # Add to balance
            if currency not in self.balances:
                self.balances[currency] = 0.0
            self.balances[currency] += amount
            
            # Record transaction
            tx = Transaction(
                tx_id=tx_id,
                tx_type="credit",
                amount=amount,
                currency=currency,
                counterparty=sender,
                reason=reason
            )
            self.transactions.append(tx)
            self._save()

        logger.info(f"💰 Received {amount} {currency} from {sender} for: {reason}")
        return tx_id

    def get_transaction_history(self, limit: int = 50) -> List[Dict]:
        """Get the recent transaction ledger."""
        sorted_txs = sorted(self.transactions, key=lambda t: t.timestamp, reverse=True)
        return [tx.to_dict() for tx in sorted_txs[:limit]]

    def get_financial_summary(self) -> str:
        """Generate a human-readable financial report."""
        lines = ["📊 **ALAS Financial Summary**"]
        lines.append("Balances:")
        for currency, amount in self.balances.items():
            lines.append(f" - {amount:.4f} {currency}")
            
        recent = self.get_transaction_history(limit=5)
        if recent:
            lines.append("\nRecent Transactions:")
            for tx in recent:
                symbol = "🔴" if tx["tx_type"] == "debit" else "🟢"
                lines.append(f" {symbol} {tx['amount']} {tx['currency']} | {tx['reason']}")
                
        return "\n".join(lines)

# Global singleton
_wallet_manager = None

def get_wallet_manager() -> WalletManager:
    global _wallet_manager
    if _wallet_manager is None:
        _wallet_manager = WalletManager()
    return _wallet_manager

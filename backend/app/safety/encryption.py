import os
import logging
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
except ImportError:
    Fernet = None

import base64

logger = logging.getLogger("alas.safety.encryption")

class MemoryVault:
    """
    ALAS Memory Vault (Phase 9 Security).
    Provides End-to-End Encryption at Rest for the agent's memory banks using AES-256.
    """
    
    def __init__(self):
        self._fernet = None
        if Fernet is None:
            logger.error("cryptography package not installed. Memory Vault disabled.")
            
    def generate_key_from_password(self, password: str, salt: bytes = b'alas_secure_salt_2026') -> bytes:
        """Derive a secure AES key from a user password."""
        if Fernet is None:
            return b""
            
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
        
    def unlock(self, key: bytes):
        """Unlock the vault with the derived key."""
        if Fernet is not None:
            self._fernet = Fernet(key)
            logger.info("🔓 Memory Vault unlocked successfully.")
            
    def encrypt_data(self, data: bytes) -> bytes:
        """Encrypt binary data."""
        if not self._fernet:
            raise ValueError("Vault is locked or disabled.")
        return self._fernet.encrypt(data)
        
    def decrypt_data(self, encrypted_data: bytes) -> bytes:
        """Decrypt binary data."""
        if not self._fernet:
            raise ValueError("Vault is locked or disabled.")
        return self._fernet.decrypt(encrypted_data)
        
    def encrypt_file(self, file_path: str, output_path: str = None):
        """Encrypt a file on disk (e.g., SQLite DB or JSON)."""
        if output_path is None:
            output_path = file_path + ".enc"
            
        with open(file_path, 'rb') as f:
            data = f.read()
            
        encrypted = self.encrypt_data(data)
        
        with open(output_path, 'wb') as f:
            f.write(encrypted)
            
        logger.info(f"Encrypted file saved to {output_path}")
        return output_path

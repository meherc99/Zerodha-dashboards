"""
Encryption utility for securing API credentials.
Uses Fernet (symmetric encryption) from cryptography library.
"""
from cryptography.fernet import Fernet
import os


class CredentialEncryption:
    """Handles encryption and decryption of sensitive credentials"""

    def __init__(self, encryption_key=None):
        """
        Initialize with encryption key.

        Args:
            encryption_key: Fernet key as bytes or string. If None, uses ENCRYPTION_KEY env var.
        """
        if encryption_key is None:
            encryption_key = os.environ.get('ENCRYPTION_KEY')

        if not encryption_key:
            raise ValueError(
                "Encryption key not provided. Set ENCRYPTION_KEY environment variable or pass key to constructor."
            )

        # Convert string key to bytes if needed
        if isinstance(encryption_key, str):
            encryption_key = encryption_key.encode()

        self.cipher = Fernet(encryption_key)

    def encrypt(self, plaintext):
        """
        Encrypt plaintext string.

        Args:
            plaintext: String to encrypt

        Returns:
            Base64 encoded encrypted string
        """
        if not plaintext:
            return None

        if isinstance(plaintext, str):
            plaintext = plaintext.encode()

        encrypted_bytes = self.cipher.encrypt(plaintext)
        return encrypted_bytes.decode()

    def decrypt(self, ciphertext):
        """
        Decrypt ciphertext string.

        Args:
            ciphertext: Base64 encoded encrypted string

        Returns:
            Decrypted plaintext string
        """
        if not ciphertext:
            return None

        if isinstance(ciphertext, str):
            ciphertext = ciphertext.encode()

        decrypted_bytes = self.cipher.decrypt(ciphertext)
        return decrypted_bytes.decode()

    @staticmethod
    def generate_key():
        """
        Generate a new Fernet encryption key.

        Returns:
            New encryption key as string
        """
        return Fernet.generate_key().decode()


# Singleton instance for app-wide use
_encryptor = None


def get_encryptor():
    """Get singleton encryption instance"""
    global _encryptor
    if _encryptor is None:
        _encryptor = CredentialEncryption()
    return _encryptor

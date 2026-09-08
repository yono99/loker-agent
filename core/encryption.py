"""Encryption module for sensitive data."""

import os
import base64
from pathlib import Path
from typing import Union, Optional
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


class EncryptionManager:
    """Manage encryption and decryption of sensitive data."""

    def __init__(self, key: Optional[str] = None):
        """Initialize encryption manager with a key.
        
        Args:
            key: Encryption key. If None, reads from ENCRYPTION_KEY environment variable.
        
        Raises:
            ValueError: If no key is provided and ENCRYPTION_KEY is not set.
        """
        self._key = key or os.environ.get("ENCRYPTION_KEY")
        if not self._key:
            raise ValueError(
                "Encryption key must be provided or set as ENCRYPTION_KEY environment variable"
            )
        self._derived_key = self._derive_key(self._key)
        self._salt = b"loker_agent_salt_2024"  # Fixed salt for reproducibility

    def _derive_key(self, key: str) -> bytes:
        """Derive a secure key from the provided key string."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._salt,
            iterations=100000,
            backend=default_backend(),
        )
        return kdf.derive(key.encode("utf-8"))

    def _pad(self, data: bytes) -> bytes:
        """Pad data to AES block size."""
        block_size = algorithms.AES.block_size // 8
        padding_len = block_size - (len(data) % block_size)
        return data + bytes([padding_len] * padding_len)

    def _unpad(self, data: bytes) -> bytes:
        """Remove padding from decrypted data."""
        padding_len = data[-1]
        if padding_len > len(data):
            raise ValueError("Invalid padding")
        return data[:-padding_len]

    def encrypt(self, data: Union[str, bytes]) -> str:
        """Encrypt data and return base64 encoded string.
        
        Args:
            data: Data to encrypt (string or bytes).
        
        Returns:
            Base64 encoded encrypted data.
        """
        if isinstance(data, str):
            data = data.encode("utf-8")
        
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(self._derived_key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        
        padded_data = self._pad(data)
        encrypted = encryptor.update(padded_data) + encryptor.finalize()
        
        # Combine IV and encrypted data, then base64 encode
        combined = iv + encrypted
        return base64.b64encode(combined).decode("ascii")

    def decrypt(self, encrypted_data: Union[str, bytes]) -> str:
        """Decrypt base64 encoded encrypted data.
        
        Args:
            encrypted_data: Base64 encoded encrypted data.
        
        Returns:
            Decrypted string.
        
        Raises:
            ValueError: If decryption fails.
        """
        if isinstance(encrypted_data, str):
            encrypted_data = encrypted_data.encode("ascii")
        
        try:
            combined = base64.b64decode(encrypted_data)
            if len(combined) < 16:
                raise ValueError("Invalid encrypted data")
            
            iv = combined[:16]
            encrypted = combined[16:]
            
            cipher = Cipher(algorithms.AES(self._derived_key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            
            decrypted_padded = decryptor.update(encrypted) + decryptor.finalize()
            decrypted = self._unpad(decrypted_padded)
            return decrypted.decode("utf-8")
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")

    def encrypt_file(self, file_path: Union[str, Path], output_path: Optional[Union[str, Path]] = None) -> str:
        """Encrypt a file.
        
        Args:
            file_path: Path to the file to encrypt.
            output_path: Path to save encrypted file. If None, appends .encrypted to original path.
        
        Returns:
            Path to the encrypted file.
        
        Raises:
            FileNotFoundError: If input file doesn't exist.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if output_path is None:
            output_path = file_path.with_suffix(file_path.suffix + ".encrypted")
        else:
            output_path = Path(output_path)
        
        with open(file_path, "rb") as f:
            data = f.read()
        
        encrypted = self.encrypt(data)
        
        with open(output_path, "w") as f:
            f.write(encrypted)
        
        return str(output_path)

    def decrypt_file(self, file_path: Union[str, Path], output_path: Optional[Union[str, Path]] = None) -> str:
        """Decrypt a file.
        
        Args:
            file_path: Path to the encrypted file.
            output_path: Path to save decrypted file. If None, removes .encrypted suffix if present.
        
        Returns:
            Path to the decrypted file.
        
        Raises:
            FileNotFoundError: If input file doesn't exist.
            ValueError: If decryption fails.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if output_path is None:
            # Remove .encrypted suffix if present
            if file_path.suffix == ".encrypted":
                output_path = file_path.with_suffix("")
            else:
                output_path = file_path.with_suffix(file_path.suffix + ".decrypted")
        else:
            output_path = Path(output_path)
        
        with open(file_path, "r") as f:
            encrypted_data = f.read().strip()
        
        decrypted = self.decrypt(encrypted_data)
        
        with open(output_path, "wb") as f:
            f.write(decrypted.encode("utf-8") if isinstance(decrypted, str) else decrypted)
        
        return str(output_path)

import keyring

from ttyf_cli.keyring.exceptions import PasswordNotFoundError


class AuthHandler:
    """Handler for secure storage and retrieval of authentication tokens."""
    
    KEYRING_SERVICE = "ttyf_plaid"
    
    @classmethod
    def save_access_token(cls, item_id: str, access_token: str) -> None:
        """
        Save a Plaid access token securely.
        
        Args:
            item_id: The Plaid item ID to use as the key
            access_token: The Plaid access token to store
        """
        keyring.set_password(cls.KEYRING_SERVICE, item_id, access_token)
    
    @classmethod
    def get_access_token(cls, item_id: str) -> str | None:
        """
        Get a Plaid access token from secure storage.
        
        Args:
            item_id: The Plaid item ID
            
        Returns:
            The access token if found, None otherwise
        """
        return keyring.get_password(cls.KEYRING_SERVICE, item_id)
    
    @classmethod
    def delete_access_token(cls, item_id: str) -> None:
        """
        Delete a Plaid access token from secure storage.
        Can raise PasswordNotFoundError if the password is not found in the keyring.
        Args:
            item_id: The Plaid item ID
        """
        try:
            keyring.delete_password(cls.KEYRING_SERVICE, item_id)
        except Exception:
            # Token might not exist, which is fine
            raise PasswordNotFoundError(f"Password for {item_id} not found in keyring.")
    
    @classmethod
    def set_link_token(cls, email: str, link_token: str) -> None:
        """
        Save a Plaid link token securely.
        
        Args:
            email: The email address to use as the key
            link_token: The Plaid link token to store
        """
        keyring.set_password(cls.KEYRING_SERVICE, email, link_token)
    
    @classmethod
    def get_link_token(cls, email: str) -> str | None:
        """
        Get a Plaid link token from secure storage.
        
        Args:
            email: The email address to use as the key
            
        Returns:
            The link token if found, None otherwise
        """
        return keyring.get_password(cls.KEYRING_SERVICE, email)
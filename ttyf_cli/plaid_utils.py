import json
import os
from ttyf_cli.schemas import PlaidConnection
from ttyf_cli.constants import _CONNECTIONS_FILE
from ttyf_cli.keyring.handler import AuthHandler
from plaid import Environment

def read_access_tokens() -> dict[str, PlaidConnection]:
    """
    Read the access tokens from the file.
    """
    with open(_CONNECTIONS_FILE, "r") as f:
        response_obj = {}
        connections = json.load(f)

        for connection in connections:
            id = connection["id"]
            access_token = AuthHandler.get_access_token(id)

            if not access_token:
                raise ValueError(f"Access token for {id} not found")

            response_obj[connection["name"]] = PlaidConnection(
                name=connection["name"],
                access_token=access_token,
                item_id=id,
            )
        

        return response_obj

def get_plaid_vars() -> tuple[str, str, Environment]:
    """
    Get the Plaid client ID and secret.
    """
    env = os.getenv("ENV", "DEV").lower()
    if env == "prod":
        return os.getenv("PLAID_CLIENT_ID"), os.getenv("PROD_PLAID_SECRET_KEY"), Environment.Production
    else:
        return os.getenv("PLAID_CLIENT_ID"), os.getenv("SANDBOX_PLAID_SECRET_KEY"), Environment.Sandbox
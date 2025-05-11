import os
import json
import time
import webbrowser
import plaid
import re

from plaid.api import plaid_api
from plaid.model.country_code import CountryCode
from plaid.model.products import Products
from plaid.model.link_token_get_request import LinkTokenGetRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.configuration import Configuration
from dotenv import load_dotenv
from rich.table import Table
from rich.progress import Progress
from ttyf_cli.plaid_utils import get_plaid_vars
from ttyf_cli.constants import _CONNECTIONS_FILE, _CREDENTIALS_FILE, _STORAGE_DIR_
from ttyf_cli.keyring.handler import AuthHandler
from ttyf_cli.keyring.exceptions import PasswordNotFoundError
from ttyf_cli.auth.plaid.callback_server import PlaidCallbackServer
from ttyf_cli.formatter import TTYFormatter

formatter = TTYFormatter()

class TTYFCommandHandler:
    """
    Command handler for the TTYF Personal Finance CLI.
    """
    def __init__(self):
        """Initialize the TTYF command handler."""
        # Load environment variables
        load_dotenv()
        
        # Set up Plaid client
        self.client_id, self.secret, self.env = get_plaid_vars()

        if not self.client_id or not self.secret:
            raise ValueError("PLAID_CLIENT_ID and PLAID_SECRET must be set")    
        
        # Configure Plaid client
        self.configuration = Configuration(
            host=self.env,
            api_key={
                'clientId': self.client_id,
                'secret': self.secret,
            }
        )
        self.client = plaid_api.PlaidApi(plaid.ApiClient(self.configuration))
        
        # Create storage directory if it doesn't exist
        self.storage_dir = _STORAGE_DIR_
        self.storage_file = _CONNECTIONS_FILE
        self.credentials_file = _CREDENTIALS_FILE
        self.storage_dir.mkdir(exist_ok=True)
        
        # Initialize connections file if it doesn't exist
        if not self.storage_file.exists():
            with open(self.storage_file, "w") as f:
                json.dump([], f)
                
        # Initialize user credentials file if it doesn't exist
        if not self.credentials_file.exists():
            with open(self.credentials_file, "w") as f:
                json.dump({}, f)

    def _save_access_token(self, name: str, access_token: str, item_id: str) -> None:
        """
        Save a Plaid access token securely.
        
        Args:
            name: A friendly name for the connection
            access_token: The Plaid access token
            item_id: The Plaid item ID
        """
        # Verify if the name already exists
        connections = self._get_connections()
        for conn in connections:
            if conn["name"] == name:
                formatter.print_error(f"Connection with name '{formatter.bold(name)}' already exists.") 
                return
        
        # Store access token securely
        AuthHandler.save_access_token(item_id, access_token)
        
        # Add connection to storage file
        connection = {
            "id": item_id,
            "name": name,
            "date_added": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        connections.append(connection)
        
        with open(self.storage_file, "w") as f:
            json.dump(connections, f, indent=2)

    def _get_connections(self) -> list[dict[str, str]]:
        """
        Get all stored Plaid connections.
        
        Returns:
            A list of connection dictionaries
        """
        if not self.storage_file.exists():
            return []
        
        with open(self.storage_file, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []

    def _get_access_token(self, item_id: str) -> str | None:
        """
        Get a Plaid access token from secure storage.
        
        Args:
            item_id: The Plaid item ID
            
        Returns:
            The access token if found, None otherwise
        """
        return AuthHandler.get_access_token(item_id)

    
    def _get_plaid_item(self, name: str) -> dict[str, str]:
        """
        Get a Plaid item from the user's account.
        """
        connections = self._get_connections()
        for conn in connections:
            if conn["name"] == name:
                return conn
        return None
    
    def _add_plaid_item(self, name: str) -> None:
        """
        Add a Plaid item to the user's account.
        
        Args:
            name: A friendly name for the connection
        """        
        # Check if connection with this name already exists
        plaid_item = self._get_plaid_item(name)
        if plaid_item:
            formatter.print_warning(f"Connection with name '{formatter.bold(name)}' already exists.")
            formatter.print(f"Remove the existing connection with: [bold]ttyf delete {formatter.bold(name)}[/bold]? (y/n)")
            confirmation = formatter.prompt("> ").strip().lower()
            if confirmation != "y":
                formatter.print("Operation cancelled.")
                return
            else:
                self._delete_plaid_item(name)
        
        # Start a local callback server
        server = PlaidCallbackServer()
        server.start()  # This starts the server in its own thread

        try:
            # Create a progress display
            task_name = formatter.start_progress(formatter.color("green", "Adding plaid connection..."), total=6)
            
            # Get user credentials
            if not self._has_user_credentials():
                self._setup_user_credentials()

            user_creds = {}
            with open(self.credentials_file, "r") as f:
                user_creds = json.load(f)
            
            # Create a link token with user's email and phone
            # Use the user's actual email if available
            email = user_creds.get("email")
            
            request = LinkTokenCreateRequest(
                user=LinkTokenCreateRequestUser(
                    client_user_id=email,
                    email_address=email,
                ),
                webhook="http://localhost:8000/auth/plaid/webhook",
                client_name="TTYF App",
                products=[Products("transactions")],
                country_codes=[CountryCode("CA")],
                language="en",
                hosted_link={
                    "completion_redirect_uri": "http://localhost:8000/oauth-callback"
                }
            )
            
            formatter.update_progress(task_name, completed=1)
            formatter.print_success("Created link token...")
            
            # Call the Plaid API to create a link token
            try:
                response = self.client.link_token_create(request)
                hosted_link_url = response['hosted_link_url']
                link_token = response['link_token']

                AuthHandler.set_link_token(email, link_token)

            except Exception as e:
                formatter.print_error(f"Failed to create link token: {str(e)}")
                return
                
            formatter.update_progress(task_name, completed=2)
            formatter.print_bold("Opening browser to connect your financial institution...")
            
            # Open the browser for the user to complete authorization
            webbrowser.open(hosted_link_url)
            formatter.print_warning("Waiting for authorization...")
            formatter.update_progress(task_name, completed=3)
            
            # Wait for user to complete authorization
            
            # Use the server's built-in wait_for_callback method
            callback_successful = server.wait_for_callback(timeout_seconds=300)
            
            if not callback_successful:
                formatter.print_error("Authorization timed out. Please try again.")
                return
            
            formatter.print_success("Recieved callback from Plaid!")
            
            # Get the public token from the server
            request = LinkTokenGetRequest(link_token=link_token)
            response = self.client.link_token_get(request)

            public_token = response['link_sessions'][-1]['results']['item_add_results'][-1]['public_token']

            if not public_token:
                formatter.print_error("No public token received. Please try again.")
                return
            
            formatter.print_success("Authorization received!")
            formatter.update_progress(task_name, completed=4)
            
            # Exchange public token for an access token
            if os.getenv("TTYF_TEST_MODE") == "1":
                # Mock values for testing or if we only received the callback but no token
                access_token = "mock-access-token-12345"
                item_id = f"mock-item-id-{int(time.time())}"
            else:
                try:
                    # Exchange the public token for an access token
                    exchange_request = ItemPublicTokenExchangeRequest(public_token=public_token)
                    exchange_response = self.client.item_public_token_exchange(exchange_request)
                    access_token = exchange_response['access_token']
                    item_id = exchange_response['item_id']
                except Exception as e:
                    formatter.print_error(f"Failed to exchange token: {str(e)}")
                    return

            formatter.update_progress(task_name, completed=5)
            
            # Save the access token
            self._save_access_token(name, access_token, item_id)
            formatter.print_success(f"Successfully added connection: {formatter.bold(name)}")
            formatter.update_progress(task_name, completed=6)
        
        except Exception as e:
            formatter.print_error(f"{str(e)}")
        
        finally:
            # Stop the progress display
            formatter.stop_progress()
            
            # Always make sure to stop the server properly
            server.stop()

    def _delete_plaid_item(self, name: str) -> None:
        """
        Delete a Plaid item from the user's account.
        
        Args:
            connection_id: The connection ID to delete
        """
        connections = self._get_connections()
        
        # Find the connection
        connection_to_remove = None
        connection_id = None
        for conn in connections:
            if conn["name"] == name:
                connection_to_remove = conn
                connection_id = conn["id"]
                break
        
        if connection_to_remove is None:
            formatter.print_error(f"Connection with name '{formatter.bold(name)}' not found.")
            return
        
        # Ask for confirmation
        name = connection_to_remove["name"]
        response = formatter.confirm(f"Are you sure you want to remove the connection to {formatter.bold(name)}?")
        if not response:
            formatter.print("Operation cancelled.")
            return
        
        # Remove from secure storage
        try:
            AuthHandler.delete_access_token(connection_id)
        except PasswordNotFoundError:
            formatter.print_error(f"Access token for {connection_id} not found in secure storage.")
            return
        
        # Remove from connections list
        connections.remove(connection_to_remove)
        
        # Save updated connections list
        with open(self.storage_file, "w") as f:
            json.dump(connections, f, indent=2)
        
        formatter.print_success(f"Successfully removed connection: {formatter.bold(name)}")
    
    def _list_plaid_items(self) -> None:
        """
        list all Plaid items for the user.
        """
        connections = self._get_connections()
        
        if not connections:
            formatter.print_color("yellow", "No financial connections found.")
            formatter.print_bold("Add a connection with: ttyf add --name <n>")
            return
        
        table = Table(title="Your Financial Connections")
        
        table.add_column("ID", style="dim")
        table.add_column("Name", style="bold")
        table.add_column("Date Added")
        
        for conn in connections:
            table.add_row(
                conn["id"],
                conn["name"],
                conn["date_added"]
            )
        
        formatter.print_table(table)
    
    def add(self, name: str, setup_creds: bool = False) -> None:
        """
        Add a new Plaid connection.
        
        Args:
            name: A friendly name for the connection
            setup_creds: Whether to set up user credentials if not already set
        """
        # Set up credentials if requested or if they don't exist
        if setup_creds or not self._has_user_credentials():
            self._setup_user_credentials()
            
        # Check if credentials exist before proceeding
        if not self._has_user_credentials():
            formatter.print_warning("User credentials not set up. Run with --setup flag to set up credentials.")
            formatter.print_bold("Example: ttyf add <n> --setup")
            return
            
        self._add_plaid_item(name)

    def delete(self, name: str) -> None:
        """
        Delete a Plaid connection.
        
        Args:
            connection_id: The ID of the connection to delete
        """
        self._delete_plaid_item(name)

    def list(self) -> None:
        """
        list all Plaid connections.
        """
        self._list_plaid_items()
        
    def _has_user_credentials(self) -> bool:
        """
        Check if user credentials are already set up.
        
        Returns:
            True if credentials exist, False otherwise
        """
        if not self.credentials_file.exists():
            return False
            
        with open(self.credentials_file, "r") as f:
            try:
                creds = json.load(f)
                return "email" in creds and "phone" in creds
            except json.JSONDecodeError:
                return False
    
    def _setup_user_credentials(self) -> None:
        """
        Set up user credentials for Plaid if they don't already exist.
        Collects email and Canadian phone number.
        """
        formatter.print_bold("Setting up user credentials for Plaid...")
        
        # Get email
        valid_email = False
        email = ""
        while not valid_email:
            email = formatter.prompt("Enter your email address:").strip()
            # Simple email validation
            if re.match(r"[^@]+@[^@]+\.[^@]+", email):
                valid_email = True
            else:
                formatter.print_error("Please enter a valid email address.")
        
        # Get Canadian phone number (9 digits)
        valid_phone = False
        phone = ""
        while not valid_phone:
            phone = formatter.prompt("Enter your Canadian phone number (10 digits only, no spaces or dashes):").strip()
            # Validate: must be 10 digits
            if re.match(r"^\d{10}$", phone):
                valid_phone = True
            else:
                formatter.print_error("Please enter exactly 10 digits for your Canadian phone number.")
        
        # Save credentials
        creds = {
            "email": email,
            "phone": phone
        }
        
        with open(self.credentials_file, "w") as f:
            json.dump(creds, f, indent=2)
            
        formatter.print_success("User credentials saved successfully!")
        
    def _show_user_credentials(self) -> None:
        """
        Display the currently stored user credentials.
        If no credentials exist, suggest setting them up.
        """
        if not self._has_user_credentials():
            formatter.print_color("yellow", "No user credentials found.")
            formatter.print_bold("Set up credentials with: ttyf user --setup")
            return
            
        with open(self.credentials_file, "r") as f:
            try:
                creds = json.load(f)
                
                table = Table(title="User Credentials")
                table.add_column("Field", style="bold")
                table.add_column("Value")
                
                email = creds.get("email", "Not set")
                phone = creds.get("phone", "Not set")
                
                # Mask phone number for privacy
                if phone and len(phone) >= 4:
                    masked_phone = "•" * (len(phone) - 4) + phone[-4:]
                else:
                    masked_phone = phone
                    
                table.add_row("Email", email)
                table.add_row("Phone", masked_phone)
                
                formatter.print_table(table)
                
            except json.JSONDecodeError:
                formatter.print_error("Could not read credentials file. It may be corrupted.")
                formatter.print_bold("Set up credentials again with: ttyf user --setup")
    
    def setup_user_credentials(self) -> None:
        """
        Public method to set up user credentials.
        """
        self._setup_user_credentials()
        
    def show_user_credentials(self) -> None:
        """
        Public method to display user credentials.
        """
        self._show_user_credentials()
import http.server
import os
import socketserver
import threading
import time
import urllib.parse
import structlog

from ttyf_cli.templates import AUTHORIZATION_COMPLETE

class PlaidCallbackServer:
    """A thread-safe callback server for Plaid Link integration."""
    
    def __init__(self, host="localhost", port=8000):
        """
        Initialize a new callback server.
        
        Args:
            host: The hostname to bind to
            port: The port to bind to
        """
        self.host = host
        self.port = port
        self.server = None
        self.thread = None
        
        # Thread-safe state
        self._lock = threading.RLock()
        self._oauth_complete = False
        
        # Register route handlers
        self.routes = {
            "/oauth-callback": self._handle_oauth_callback,
        }
    
    def _create_request_handler(self):
        """Create a request handler class with access to the callback server."""
        server = self
        
        class CallbackRequestHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                """Handle GET requests by routing to appropriate handler."""
                parsed_path = urllib.parse.urlparse(self.path)
                parsed_query = urllib.parse.parse_qs(parsed_path.query)
                
                # Find and execute the matching route handler
                handler = server.routes.get(parsed_path.path)
                if handler:
                    handler(self, parsed_path, parsed_query)
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args):
                """Suppress logging output."""
                return
        
        return CallbackRequestHandler

    
    def _handle_oauth_callback(self, request, path, query):
        """
        Handle OAuth callback from Plaid.
        
        Args:
            request: The HTTP request object
            path: The parsed URL path
            query: The parsed query parameters
        """
        with self._lock:
            self._oauth_complete = True
        
        # Send success response
        request.send_response(200)
        request.send_header("Content-type", "text/html")
        request.end_headers()
        request.wfile.write(AUTHORIZATION_COMPLETE.encode())

    def start(self):
        """Start the callback server in a separate thread."""
        if self.server:
            return  # Server already running
        
        # Create and configure the server
        handler_class = self._create_request_handler()
        self.server = socketserver.TCPServer((self.host, self.port), handler_class)
        self.server.allow_reuse_address = True
        
        # Run server in a separate thread
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self):
        """Stop the callback server if it's running."""
        if not self.server:
            return  # Server not running
        
        self.server.shutdown()
        self.server.server_close()
        self.server = None
        self.thread.join()
    
    def wait_for_callback(self, timeout_seconds=300):
        """
        Wait for a callback to be received.
        
        Args:
            timeout_seconds: Maximum time to wait in seconds
            
        Returns:
            True if a callback was received, False if timed out
        """
        start_time = time.time()
        
        # For testing purposes
        if os.getenv("TTYF_TEST_MODE") == "1":
            time.sleep(1)  # Simulate a delay
            with self._lock:
                self._oauth_complete = True
            return True
        
        # Wait for a callback to complete or timeout
        while True:
            if self.is_oauth_complete:
                return True
            
            if time.time() - start_time > timeout_seconds:
                return False
            
            time.sleep(0.5)  # Check every half second
    
    @property
    def is_oauth_complete(self):
        """Check if OAuth callback was received, thread-safe."""
        with self._lock:
            return self._oauth_complete
    
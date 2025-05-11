import time
from rich.console import Console
from rich.progress import Progress, TaskID
from rich.table import Table
from rich.panel import Panel

class TTYFormatter:
    """
    Formatter utility for TTYF CLI that provides consistent styling and output methods.
    Wraps around Rich's Console and Progress classes.
    """
    
    def __init__(self):
        """Initialize the formatter with a Rich console."""
        self.console = Console()
        self._active_progress: Progress | None = None
        self._active_tasks: dict[str, TaskID] = {}
    
    def print(self, message: str, **kwargs) -> None:
        """Print a message to the console."""
        self.console.print(message, **kwargs)
    
    def print_bold(self, message: str, **kwargs) -> None:
        """Print a message in bold format."""
        self.console.print(f"[bold]{message}[/bold]", **kwargs)
    
    def print_color(self, color: str, message: str, **kwargs) -> None:
        """
        Print a message in the specified color.
        
        Args:
            color: Color name (e.g., 'red', 'green', 'blue', 'yellow')
            message: The message to print
            **kwargs: Additional arguments to pass to console.print
        """
        self.console.print(f"[{color}]{message}[/{color}]", **kwargs)
    
    def print_error(self, message: str, **kwargs) -> None:
        """Print an error message (bold red)."""
        self.console.print(f"[bold red]Error:[/bold red] {message}", **kwargs)
    
    def print_warning(self, message: str, **kwargs) -> None:
        """Print a warning message (bold yellow)."""
        self.console.print(f"[bold yellow]Warning:[/bold yellow] {message}", **kwargs)
    
    def print_success(self, message: str, **kwargs) -> None:
        """Print a success message (green checkmark + message)."""
        self.console.print(f"[green]✓[/green] {message}", **kwargs)
    
    def print_info(self, message: str, **kwargs) -> None:
        """Print an info message (blue)."""
        self.console.print(f"[blue]ℹ[/blue] {message}", **kwargs)
    
    def print_panel(self, message: str, title: str | None = None, **kwargs) -> None:
        """Print a message in a panel with optional title."""
        panel = Panel(message, title=title, **kwargs)
        self.console.print(panel)
    
    def create_table(self, title: str | None = None, **kwargs) -> Table:
        """Create and return a Rich table object with the given title."""
        return Table(title=title, **kwargs)
    
    def print_table(self, table: Table) -> None:
        """Print a Rich table."""
        self.console.print(table)
    
    def start_progress(self, description: str, total: int = 100) -> str:
        """
        Start a progress bar and return its identifier.
        
        Args:
            description: The description of the task
            total: The total number of steps
            
        Returns:
            A string identifier for the task
        """
        if self._active_progress is None:
            self._active_progress = Progress()
            self._active_progress.__enter__()
        
        task_id = self._active_progress.add_task(description, total=total)
        task_name = f"task_{time.time()}"
        self._active_tasks[task_name] = task_id
        return task_name
    
    def update_progress(self, task_name: str, advance: float | None = None, 
                       completed: float | None = None, description: str | None = None) -> None:
        """
        Update a progress bar.
        
        Args:
            task_name: The task identifier returned by start_progress
            advance: How much to advance the progress bar
            completed: Set the progress bar to this value
            description: Update the description text
        """
        if self._active_progress is None or task_name not in self._active_tasks:
            return
            
        kwargs = {}
        if advance is not None:
            kwargs["advance"] = advance
        if completed is not None:
            kwargs["completed"] = completed
        if description is not None:
            kwargs["description"] = description
            
        self._active_progress.update(self._active_tasks[task_name], **kwargs)
    
    def complete_progress(self, task_name: str) -> None:
        """
        Mark a progress task as completed.
        
        Args:
            task_name: The task identifier returned by start_progress
        """
        if self._active_progress is None or task_name not in self._active_tasks:
            return
            
        self._active_progress.update(self._active_tasks[task_name], completed=100)
    
    def stop_progress(self) -> None:
        """Stop all progress bars and clean up."""
        if self._active_progress is not None:
            self._active_progress.__exit__(None, None, None)
            self._active_progress = None
            self._active_tasks = {}
    
    def prompt(self, message: str, default: str = "", password: bool = False) -> str:
        """
        Prompt the user for input.
        
        Args:
            message: The prompt message
            default: Default value if user enters nothing
            password: Whether to hide the input (for passwords)
            
        Returns:
            The user's input
        """
        return self.console.input(f"{message} ", password=password) or default
    
    def confirm(self, message: str, default: bool = False) -> bool:
        """
        Ask the user for confirmation.
        
        Args:
            message: The confirmation message
            default: Default value if user enters nothing
            
        Returns:
            True if confirmed, False otherwise
        """
        suffix = " (y/n) " if default is None else " (Y/n) " if default else " (y/N) "
        response = self.console.input(f"{message}{suffix}").strip().lower()
        
        if not response:
            return default
            
        return response[0] == 'y'
    
    def color(self, color: str, message: str) -> str:
        """
        Color a message.
        """
        return f"[{color}]{message}[/{color}]"
    
    def bold(self, message: str) -> str:
        """
        Bold a message.
        """
        return f"[bold]{message}[/bold]"
    
    
    
    
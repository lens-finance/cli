import os
import click
from ttyf_cli.ttyf import TTYFCommandHandler



@click.group()
@click.version_option(version="0.1.0")
def cli_entrypoint():
    """
    TTYF - Track The YF (Your Finances) CLI.
    
    A command-line tool to manage your Plaid connections for personal finance tracking.
    """
    pass


@cli_entrypoint.command(name="add")
@click.argument("name")
@click.option("--setup", is_flag=True, help="Set up user credentials for Plaid if not already set")
def add_connection(name, setup):
    """Add a new financial institution connection through Plaid."""
    handler = TTYFCommandHandler()
    handler.add(name=name, setup_creds=setup)


@cli_entrypoint.command(name="list")
def list_connections():
    """List all your financial institution connections."""
    handler = TTYFCommandHandler()
    handler.list()


@cli_entrypoint.command(name="remove")
@click.argument("name")
def remove_connection(name):
    """Remove a financial institution connection."""
    handler = TTYFCommandHandler()
    handler.delete(name=name)


@cli_entrypoint.command(name="user")
@click.option("--setup", is_flag=True, help="Set up user credentials for Plaid")
@click.option("--show", is_flag=True, help="Show current user credentials")
def manage_user(setup, show):
    """Manage user credentials for Plaid."""
    handler = TTYFCommandHandler()
    
    if setup:
        handler.setup_user_credentials()
    elif show:
        handler.show_user_credentials()
    else:
        # Default to showing credentials if no option is provided
        handler.show_user_credentials()


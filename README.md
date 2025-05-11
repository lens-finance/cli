# TTYF CLI (Talk To Your Finances)

A command-line tool to manage your Plaid connections for personal finance tracking.

## Installation

```bash
# Using pip
pip install -e .

# Or using uv
uv pip install -e .
```

## Usage

```bash
# Add a new connection
ttyf add <name> [--setup]

# List all connections
ttyf list

# Remove a connection
ttyf remove <name>

# Manage user credentials
ttyf user [--setup] [--show]
```

## Development

This CLI works with the TTYF MCP Server to provide personal finance functionality.
#!/usr/bin/env python3
"""
Simulation Manager - A tool to manage local simulation projects

This is the main entry point that routes commands to their respective modules.
"""

import sys
import argparse
from pathlib import Path

# Import command handlers
from commands import (
    add_command,
    list_command,
    remove_command,
    pull_command,
    run_command,
    extract_and_link_fields_command,
)


def main():
    parser = argparse.ArgumentParser(
        description='Simulation Manager - Manage local simulation projects'
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add a GitHub project to Local_Simulations')
    add_parser.add_argument('url', help='GitHub repository URL')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List downloaded projects')
    
    # Remove command
    remove_parser = subparsers.add_parser('remove', help='Remove a project from Local_Simulations')
    remove_parser.add_argument('name', help='Name of the directory to remove')
    
    # Pull command
    pull_parser = subparsers.add_parser('pull', help='Run git pull for all repositories')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run manager.py in a project directory')
    run_parser.add_argument('name', nargs='?', default=None, help='Name of the project directory to run (optional - will prompt if not provided)')
    
    # Dev command with subcommands
    dev_parser = subparsers.add_parser('dev', help='Development utilities')
    dev_subparsers = dev_parser.add_subparsers(dest='dev_command', help='Dev commands')
    
    # Dev extract_and_link_fields command
    extract_parser = dev_subparsers.add_parser(
        'extract_and_link_fields',
        help='Extract variables from Python files and link to value.txt'
    )
    extract_parser.add_argument('directory', help='Directory containing Python files to process')
    
    args = parser.parse_args()
    
    # Route to appropriate command handler
    if args.command == 'add':
        add_command(args)
    elif args.command == 'list':
        list_command(args)
    elif args.command == 'remove':
        remove_command(args)
    elif args.command == 'pull':
        pull_command(args)
    elif args.command == 'run':
        run_command(args)
    elif args.command == 'dev':
        if args.dev_command == 'extract_and_link_fields':
            extract_and_link_fields_command(args)
        else:
            dev_parser.print_help()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

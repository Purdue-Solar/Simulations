#!/usr/bin/env python3
"""
Simulation Manager - A tool to manage local simulation projects
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


def clone_github_repo(github_url, target_dir):
    """
    Clone a GitHub repository into the target directory.
    
    Args:
        github_url: The GitHub repository URL
        target_dir: The directory to clone into
    """
    # Validate the URL
    parsed_url = urlparse(github_url)
    if 'github.com' not in parsed_url.netloc:
        print(f"Error: Invalid GitHub URL: {github_url}", file=sys.stderr)
        sys.exit(1)
    
    # Create target directory if it doesn't exist
    target_path = Path(target_dir)
    target_path.mkdir(parents=True, exist_ok=True)
    
    # Extract repo name from URL
    repo_name = parsed_url.path.strip('/').split('/')[-1]
    if repo_name.endswith('.git'):
        repo_name = repo_name[:-4]
    
    destination = target_path / repo_name
    
    # Check if directory already exists
    if destination.exists():
        print(f"Error: Directory '{destination}' already exists!", file=sys.stderr)
        sys.exit(1)
    
    # Clone the repository
    print(f"Cloning {github_url} into {destination}...")
    try:
        result = subprocess.run(
            ['git', 'clone', github_url, str(destination)],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"✓ Successfully cloned to {destination}")
    except subprocess.CalledProcessError as e:
        print(f"Error cloning repository: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: Git is not installed or not in PATH", file=sys.stderr)
        sys.exit(1)


def add_command(args):
    """Handle the add command"""
    local_simulations_dir = Path(__file__).parent / "Local_Simulations"
    clone_github_repo(args.url, local_simulations_dir)


def list_command(args):
    """Handle the list command"""
    local_simulations_dir = Path(__file__).parent / "Local_Simulations"
    
    if not local_simulations_dir.exists():
        print("Local_Simulations directory does not exist yet.")
        print("Use 'add' command to download a project first.")
        return
    
    # Get all directories in Local_Simulations
    directories = [d for d in local_simulations_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
    
    if not directories:
        print("No projects found in Local_Simulations.")
        return
    
    print(f"Downloaded projects in Local_Simulations ({len(directories)}):")
    print()
    for directory in sorted(directories):
        # Check if it's a git repository
        is_git = (directory / ".git").exists()
        git_indicator = " [git]" if is_git else ""
        print(f"  • {directory.name}{git_indicator}")


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
    
    args = parser.parse_args()
    
    if args.command == 'add':
        add_command(args)
    elif args.command == 'list':
        list_command(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

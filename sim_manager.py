#!/usr/bin/env python3
"""
Simulation Manager - A tool to manage local simulation projects
"""

import argparse
import os
import shutil
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


def remove_command(args):
    """Handle the remove command"""
    local_simulations_dir = Path(__file__).parent / "Local_Simulations"
    
    if not local_simulations_dir.exists():
        print(f"Error: Local_Simulations directory does not exist.", file=sys.stderr)
        sys.exit(1)
    
    target_dir = local_simulations_dir / args.name
    
    if not target_dir.exists():
        print(f"Error: Directory '{args.name}' not found in Local_Simulations.", file=sys.stderr)
        sys.exit(1)
    
    if not target_dir.is_dir():
        print(f"Error: '{args.name}' is not a directory.", file=sys.stderr)
        sys.exit(1)
    
    # Remove the directory
    print(f"Removing {target_dir}...")
    try:
        shutil.rmtree(target_dir)
        print(f"✓ Successfully removed {args.name}")
    except Exception as e:
        print(f"Error removing directory: {e}", file=sys.stderr)
        sys.exit(1)


def pull_command(args):
    """Handle the pull command"""
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
    
    # Filter for git repositories
    git_repos = [d for d in directories if (d / ".git").exists()]
    
    if not git_repos:
        print("No git repositories found in Local_Simulations.")
        return
    
    print(f"Pulling updates for {len(git_repos)} repositories...\n")
    
    success_count = 0
    error_count = 0
    
    for repo in sorted(git_repos):
        print(f"📦 {repo.name}:")
        try:
            result = subprocess.run(
                ['git', '-C', str(repo), 'pull'],
                check=True,
                capture_output=True,
                text=True
            )
            output = result.stdout.strip()
            if "Already up to date" in output or "Already up-to-date" in output:
                print(f"   ✓ Already up to date")
            else:
                print(f"   ✓ Updated")
                if output:
                    for line in output.split('\n')[:3]:  # Show first 3 lines
                        print(f"     {line}")
            success_count += 1
        except subprocess.CalledProcessError as e:
            print(f"   ✗ Error: {e.stderr.strip()}")
            error_count += 1
        print()
    
    print(f"Summary: {success_count} succeeded, {error_count} failed")


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
    
    args = parser.parse_args()
    
    if args.command == 'add':
        add_command(args)
    elif args.command == 'list':
        list_command(args)
    elif args.command == 'remove':
        remove_command(args)
    elif args.command == 'pull':
        pull_command(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

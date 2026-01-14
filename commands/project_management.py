"""Project management commands: add, list, remove, pull"""

import sys
import subprocess
import shutil
from pathlib import Path
from urllib.parse import urlparse


# Import for running dev command after pull
def _run_dev_extract(repo_path):
    """Run the dev extract_and_link_fields command on a repository.
    
    Args:
        repo_path: Path to the repository directory
    """
    from .dev_tools import extract_and_link_fields_command
    import argparse
    
    # Create a mock args object for the dev command
    mock_args = argparse.Namespace(directory=str(repo_path))
    
    try:
        extract_and_link_fields_command(mock_args)
    except Exception as e:
        print(f"   ⚠ Warning: Failed to regenerate manager.py: {e}")


def _initialize_project(repo_path, verbose=True):
    """Initialize a project by running uv sync and dev extract.
    
    Args:
        repo_path: Path to the repository directory
        verbose: Whether to print progress messages
    """
    repo_path = Path(repo_path)
    
    # Check if pyproject.toml or requirements.txt exists
    has_pyproject = (repo_path / "pyproject.toml").exists()
    has_requirements = (repo_path / "requirements.txt").exists()
    
    if has_pyproject or has_requirements:
        if verbose:
            print(f"→ Installing dependencies with uv sync...")
        try:
            result = subprocess.run(
                ['uv', 'sync'],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                check=True
            )
            if verbose:
                print(f"✓ Dependencies installed")
        except subprocess.CalledProcessError as e:
            if verbose:
                print(f"⚠ Warning: uv sync failed: {e.stderr.strip()}")
        except FileNotFoundError:
            if verbose:
                print(f"⚠ Warning: uv not found, skipping dependency installation")
    
    # Run dev extract
    if verbose:
        print(f"→ Setting up project configuration...")
    _run_dev_extract(repo_path)
    if verbose:
        print(f"✓ Configuration ready")



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
    local_simulations_dir = Path(__file__).parent.parent / "Local_Simulations"
    clone_github_repo(args.url, local_simulations_dir)
    
    # Extract repo name to show helpful message
    parsed_url = urlparse(args.url)
    repo_name = parsed_url.path.strip('/').split('/')[-1]
    if repo_name.endswith('.git'):
        repo_name = repo_name[:-4]
    
    cloned_dir = local_simulations_dir / repo_name
    
    # Automatically initialize the project (uv sync + dev extract)
    print()
    _initialize_project(cloned_dir, verbose=True)
    print(f"\n✓ Project ready! Run: python3 {cloned_dir / 'manager.py'}")


def list_command(args):
    """Handle the list command"""
    local_simulations_dir = Path(__file__).parent.parent / "Local_Simulations"
    
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
    local_simulations_dir = Path(__file__).parent.parent / "Local_Simulations"
    
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
    local_simulations_dir = Path(__file__).parent.parent / "Local_Simulations"
    
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
        
        # Step 1: Reset hard to discard local changes
        print(f"   → Resetting local changes...")
        try:
            subprocess.run(
                ['git', '-C', str(repo), 'reset', '--hard'],
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            print(f"   ✗ Error resetting: {e.stderr.strip()}")
            error_count += 1
            print()
            continue
        
        # Step 2: Remove manager.py if it exists
        manager_file = repo / "manager.py"
        if manager_file.exists():
            try:
                manager_file.unlink()
                print(f"   → Removed manager.py")
            except Exception as e:
                print(f"   ⚠ Warning: Could not remove manager.py: {e}")
        
        # Step 3: Pull updates
        print(f"   → Pulling updates...")
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
                # Show first line of output for context
                first_line = output.split('\n')[0]
                print(f"     {first_line}")
            
            # Step 4: Reinitialize project (uv sync + regenerate manager.py)
            print(f"   → Reinitializing project...")
            _initialize_project(repo, verbose=False)
            print(f"   ✓ Project reinitialized")
            
            success_count += 1
        except subprocess.CalledProcessError as e:
            print(f"   ✗ Error pulling: {e.stderr.strip()}")
            error_count += 1
        print()
    
    print(f"Summary: {success_count} succeeded, {error_count} failed")


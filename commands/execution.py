"""Execution commands: run"""

import sys
import subprocess
from pathlib import Path


def run_command(args):
    """Handle the run command - with optional interactive project selection"""
    local_simulations_dir = Path(__file__).parent.parent / "Local_Simulations"
    
    if not local_simulations_dir.exists():
        print(f"Error: Local_Simulations directory does not exist.", file=sys.stderr)
        sys.exit(1)
    
    # If no directory specified, show interactive prompt
    if args.name is None:
        target_dir = _select_project_interactively(local_simulations_dir)
    else:
        target_dir = local_simulations_dir / args.name
        
        if not target_dir.exists():
            print(f"Error: Directory '{args.name}' not found in Local_Simulations.", file=sys.stderr)
            sys.exit(1)
        
        if not target_dir.is_dir():
            print(f"Error: '{args.name}' is not a directory.", file=sys.stderr)
            sys.exit(1)
    
    manager_file = target_dir / "manager.py"
    
    if not manager_file.exists():
        print(f"Error: manager.py not found in '{target_dir.name}'.", file=sys.stderr)
        print(f"\nTo initialize interactive mode, run:", file=sys.stderr)
        print(f"  python3 sim_manager.py dev extract_and_link_fields {target_dir}", file=sys.stderr)
        sys.exit(1)
    
    # Run manager.py
    print(f"Running {manager_file}...\n")
    try:
        result = subprocess.run(
            [sys.executable, str(manager_file)],
            cwd=str(target_dir),
            check=False
        )
        sys.exit(result.returncode)
    except Exception as e:
        print(f"Error running manager.py: {e}", file=sys.stderr)
        sys.exit(1)


def _select_project_interactively(local_simulations_dir):
    """Display interactive prompt to select a project.
    
    Args:
        local_simulations_dir: Path to Local_Simulations directory
        
    Returns:
        Path: Selected project directory
    """
    # Get all directories with manager.py
    projects = []
    for item in sorted(local_simulations_dir.iterdir()):
        if item.is_dir() and (item / "manager.py").exists():
            projects.append(item)
    
    if not projects:
        print("No projects found with manager.py.", file=sys.stderr)
        print("\nUse 'add' command to download a project, or run:", file=sys.stderr)
        print("  python3 sim_manager.py dev extract_and_link_fields <directory>", file=sys.stderr)
        sys.exit(1)
    
    # Display project selection menu
    print("=" * 60)
    print("  Simulation Manager - Project Selection")
    print("=" * 60)
    print("\nAvailable projects:")
    print()
    
    for i, project in enumerate(projects, 1):
        print(f"  {i}. {project.name}")
    
    print()
    
    # Get user selection
    while True:
        choice = input(f"Select project to run (1-{len(projects)}) or 'q' to quit: ").strip()
        if choice.lower() == 'q':
            print("Exiting...")
            sys.exit(0)
        
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(projects):
                selected_project = projects[choice_num - 1]
                print()
                print(f"Selected: {selected_project.name}")
                print("-" * 60)
                print()
                return selected_project
            else:
                print(f"Please enter a number between 1 and {len(projects)}")
        except ValueError:
            print("Invalid input. Please enter a number or 'q'")

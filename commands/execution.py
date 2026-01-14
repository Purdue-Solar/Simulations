"""Execution commands: run"""

import sys
import subprocess
from pathlib import Path


def run_command(args):
    """Handle the run command"""
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
    
    manager_file = target_dir / "manager.py"
    
    if not manager_file.exists():
        print(f"Error: manager.py not found in '{args.name}'.", file=sys.stderr)
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

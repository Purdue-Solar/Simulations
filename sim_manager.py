#!/usr/bin/env python3
"""
Simulation Manager - A tool to manage local simulation projects
"""

import argparse
import ast
import json
import os
import re
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
    
    # Extract repo name to show helpful message
    parsed_url = urlparse(args.url)
    repo_name = parsed_url.path.strip('/').split('/')[-1]
    if repo_name.endswith('.git'):
        repo_name = repo_name[:-4]
    
    cloned_dir = local_simulations_dir / repo_name
    
    # Check if manager.py exists (project already initialized)
    manager_file = cloned_dir / "manager.py"
    if manager_file.exists():
        print(f"\n✓ Project already has manager.py")
        print(f"  Run: python3 {manager_file}")
    else:
        print(f"\n💡 To enable interactive mode, run:")
        print(f"  python3 sim_manager.py dev extract_and_link_fields {cloned_dir}")


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


def run_command(args):
    """Handle the run command"""
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


def extract_and_link_fields_command(args):
    """Handle the dev extract_and_link_fields command"""
    directory = Path(args.directory)
    
    if not directory.exists():
        print(f"Error: Directory '{directory}' does not exist.", file=sys.stderr)
        sys.exit(1)
    
    if not directory.is_dir():
        print(f"Error: '{directory}' is not a directory.", file=sys.stderr)
        sys.exit(1)
    
    # Find all Python files in the directory
    python_files = sorted(directory.glob("*.py"))
    
    if not python_files:
        print(f"No Python files found in '{directory}'.")
        return
    
    print(f"Extracting variables from {len(python_files)} Python files...\n")
    
    # Store extracted variables: {filename: [(var_name, value, line_num, col_offset)]}
    extracted_vars = {}
    
    for py_file in python_files:
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
                tree = ast.parse(content, filename=str(py_file))
            
            file_vars = []
            
            # Extract only top-level (module-level) variable assignments
            for node in tree.body:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            var_name = target.id
                            # Skip private variables
                            if var_name.startswith('_'):
                                continue
                                
                            # Try to get the value
                            try:
                                value = ast.literal_eval(node.value)
                            except (ValueError, TypeError):
                                # For non-literal values, get the source representation
                                try:
                                    value = ast.get_source_segment(content, node.value)
                                    if value is None:
                                        value = "<complex_expression>"
                                except:
                                    value = "<complex_expression>"
                            
                            # Mark this as a complex expression if it's not a simple literal
                            is_expression = not isinstance(node.value, (ast.Constant, ast.List, ast.Dict, ast.Tuple))
                            
                            file_vars.append((var_name, value, node.lineno, node.col_offset, is_expression))
            
            if file_vars:
                extracted_vars[py_file.name] = file_vars
                print(f"✓ {py_file.name}: {len(file_vars)} variables found")
            else:
                print(f"  {py_file.name}: No variables found")
        
        except SyntaxError as e:
            print(f"✗ {py_file.name}: Syntax error - {e}")
        except Exception as e:
            print(f"✗ {py_file.name}: Error - {e}")
    
    if not extracted_vars:
        print("\nNo variables extracted.")
        return
    
    # Prepare configuration data for JSON format
    config_data = {}
    for filename, vars_list in extracted_vars.items():
        config_data[filename] = {}
        for var_name, value, line_num, _, is_expression in vars_list:
            # Skip complex expressions - they can't be configured via command line
            # More strict filtering: only include simple literals
            if is_expression:
                continue
            if isinstance(value, str):
                # Skip strings that look like expressions
                if value.startswith("<") or any(op in value for op in ["math.", "+", "-", "*", "/", "(", ")", "[", "]"]):
                    continue
                
            # Determine type
            var_type = "str"
            if isinstance(value, bool):
                var_type = "bool"
            elif isinstance(value, int):
                var_type = "int"
            elif isinstance(value, float):
                var_type = "float"
            
            arg_name = var_name.lower().replace('_', '-')
            
            config_data[filename][var_name] = {
                "value": value,
                "type": var_type,
                "arg": f"--{arg_name}",
                "line": line_num
            }
    
    # Now modify source files to use command-line arguments
    print("\nModifying source files to use command-line arguments...")
    
    for py_file in python_files:
        if py_file.name not in extracted_vars:
            continue
        
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            vars_list = sorted(extracted_vars[py_file.name], key=lambda x: x[2])  # Sort by line number
            
            # Separate configurable vars from expression vars
            configurable_vars = []
            for v in vars_list:
                if v[4]:  # is_expression
                    continue
                if isinstance(v[1], str) and (v[1].startswith("<") or any(op in v[1] for op in ["math.", "+", "-", "*", "/", "(", ")", "[", "]"])):
                    continue
                configurable_vars.append((v[0], v[1], v[2], v[3]))
            
            if not configurable_vars:
                print(f"  {py_file.name}: No configurable variables (only expressions)")
                continue
            
            if not configurable_vars:
                print(f"  {py_file.name}: No configurable variables (only expressions)")
                continue
            
            # Check if argparse is already imported
            has_argparse = any('import argparse' in line for line in lines)
            has_sys = any('import sys' in line for line in lines)
            
            # Find where to insert imports (after shebang and docstrings)
            import_pos = 0
            if lines and lines[0].startswith('#!'):
                import_pos = 1
            
            # Skip module docstrings
            while import_pos < len(lines):
                stripped = lines[import_pos].strip()
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    quote = '"""' if '"""' in stripped else "'''"
                    if stripped.count(quote) >= 2:
                        import_pos += 1
                        break
                    import_pos += 1
                    while import_pos < len(lines) and quote not in lines[import_pos]:
                        import_pos += 1
                    import_pos += 1
                    break
                elif stripped and not stripped.startswith('#'):
                    break
                elif stripped.startswith('#'):
                    import_pos += 1
                else:
                    import_pos += 1
            
            # Add necessary imports
            imports_to_add = []
            if not has_argparse:
                imports_to_add.append("import argparse\n")
            if not has_sys:
                imports_to_add.append("import sys\n")
            
            # Track total lines inserted for offset calculation
            lines_inserted_count = 0
            
            if imports_to_add:
                # Find existing import block
                while import_pos < len(lines) and (lines[import_pos].strip().startswith('import') or 
                                                    lines[import_pos].strip().startswith('from') or
                                                    not lines[import_pos].strip()):
                    import_pos += 1
                
                for imp in imports_to_add:
                    lines.insert(import_pos, imp)
                    import_pos += 1
                    lines_inserted_count += 1
                if not lines[import_pos-1].strip():
                    pass  # Already have blank line
                else:
                    lines.insert(import_pos, "\n")
                    import_pos += 1
                    lines_inserted_count += 1
            
            # Generate argument parser code
            parser_code = [
                "\n# Parse command-line arguments (auto-generated)\n",
                "parser = argparse.ArgumentParser(description='Configuration variables')\n"
            ]
            
            for var_name, value, line_num, _ in configurable_vars:
                # Determine type and format default
                default_str = f'"{value}"' if isinstance(value, str) and not value.startswith("<") else str(value)
                
                # Set the actual type for argparse (not a string)
                if isinstance(value, bool):
                    # Special handling for bool since argparse doesn't handle it well
                    arg_name = var_name.lower().replace('_', '-')
                    parser_code.append(f"parser.add_argument('--{arg_name}', type=lambda x: x.lower() in ['true', '1', 'yes', 'y'], default={default_str}, help='{var_name} (default: {default_str})')\n")
                elif isinstance(value, int):
                    arg_name = var_name.lower().replace('_', '-')
                    parser_code.append(f"parser.add_argument('--{arg_name}', type=int, default={default_str}, help='{var_name} (default: {default_str})')\n")
                elif isinstance(value, float):
                    arg_name = var_name.lower().replace('_', '-')
                    parser_code.append(f"parser.add_argument('--{arg_name}', type=float, default={default_str}, help='{var_name} (default: {default_str})')\n")
                else:
                    # String or complex expression
                    arg_name = var_name.lower().replace('_', '-')
                    parser_code.append(f"parser.add_argument('--{arg_name}', type=str, default={default_str}, help='{var_name} (default: {default_str})')\n")
            
            parser_code.append("args = parser.parse_args()\n\n")
            
            # Find where to insert parser code - right after imports and before first variable
            # We need to find a safe place that won't overwrite any variables
            insert_pos = import_pos  # Start from end of imports
            
            # Insert parser code at the safe position
            for code_line in reversed(parser_code):
                lines.insert(insert_pos, code_line)
                lines_inserted_count += 1
            
            # Now replace variable assignments with argument references
            # We need to adjust line numbers after insertions
            offset = lines_inserted_count  # Total lines inserted (imports + parser code)
            
            # Create a set of configurable variable names for quick lookup
            configurable_var_names = {v[0] for v in configurable_vars}
            
            # Build a mapping of line numbers to replacement text for configurable vars only
            # This ensures we don't accidentally modify expression variable lines
            lines_to_replace = {}
            replaced_vars = set()
            
            for var_name, value, line_num, _, is_expr in vars_list:
                # Skip if already replaced (handles duplicate variable names)
                if var_name in replaced_vars:
                    continue
                
                # Skip expression variables - they must remain unchanged
                if is_expr:
                    replaced_vars.add(var_name)
                    continue
                
                # Skip if not in configurable list
                if var_name not in configurable_var_names:
                    continue
                    
                adjusted_line = line_num - 1 + offset  # Adjust for inserted parser code
                arg_attr = var_name.lower().replace('_', '-').replace('-', '_')
                
                # Get the original line to preserve formatting
                old_line = lines[adjusted_line]
                
                # Extract indentation (leading whitespace)
                indent_match = re.match(r'^(\s*)', old_line)
                indent = indent_match.group(1) if indent_match else ''
                
                # Check if there's an inline comment to preserve
                comment_match = re.search(r'#.*$', old_line)
                comment = '  ' + comment_match.group(0) if comment_match else ''
                
                # Create new line with preserved indentation and optional comment
                new_line = f"{indent}{var_name} = args.{arg_attr}{comment}\n"
                lines_to_replace[adjusted_line] = new_line
                replaced_vars.add(var_name)
            
            # Apply all replacements
            for line_num, new_content in lines_to_replace.items():
                lines[line_num] = new_content
            
            # Write modified file
            with open(py_file, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            print(f"✓ Modified {py_file.name} to use {len(configurable_vars)} command-line arguments")
        
        except Exception as e:
            print(f"✗ Error modifying {py_file.name}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n✓ Extraction and modification complete!")
    print(f"  Total variables: {sum(len(v) for v in extracted_vars.values())}")
    print(f"\nVariables can now be set via command-line arguments:")
    for filename, vars_list in sorted(extracted_vars.items()):
        # Filter to only show configurable variables
        configurable = []
        for v in vars_list:
            if v[4]:  # is_expression
                continue
            if isinstance(v[1], str) and (v[1].startswith("<") or any(op in v[1] for op in ["math.", "+", "-", "*", "/", "(", ")", "[", "]"])):
                continue
            configurable.append(v)
        
        if not configurable:
            continue
        print(f"\n  {filename}:")
        for var_name, value, _, _, _ in sorted(configurable, key=lambda x: x[2])[:3]:  # Show first 3
            arg_name = var_name.lower().replace('_', '-')
            print(f"    --{arg_name}")
        if len(configurable) > 3:
            print(f"    ... and {len(configurable) - 3} more")
    
    # Create manager.py
    print("\nCreating manager.py...")
    create_manager_script(directory, python_files, config_data)
    print("✓ Created manager.py for interactive execution (self-contained)")


def create_manager_script(directory, python_files, config_data):
    """Create a manager.py script for interactive execution"""
    manager_path = directory / "manager.py"
    
    # Convert config_data to a formatted Python dictionary string
    config_str = json.dumps(config_data, indent=2)
    
    # Write the manager script with embedded configuration
    with open(manager_path, 'w', encoding='utf-8') as f:
        f.write('#!/usr/bin/env python3\n')
        f.write('"""\n')
        f.write('Interactive Manager for Simulation Scripts\n')
        f.write('Auto-generated by sim_manager.py\n')
        f.write('Contains embedded configuration from value.txt\n')
        f.write('"""\n\n')
        f.write('import subprocess\n')
        f.write('import sys\n')
        f.write('from pathlib import Path\n\n\n')
        f.write('# Embedded configuration (auto-generated from value.txt)\n')
        f.write(f'CONFIG = {config_str}\n\n\n')
        f.write('def load_config():\n')
        f.write('    """Load embedded configuration"""\n')
        f.write('    return CONFIG\n\n\n')
        f.write('def get_user_input(prompt, default_value, var_type):\n')
        f.write('    """Get user input with default value support"""\n')
        f.write('    type_hint = f" ({var_type})" if var_type != "str" else ""\n')
        f.write('    user_input = input(f"{prompt}{type_hint} [{default_value}]: ").strip()\n')
        f.write('    \n')
        f.write('    if not user_input:\n')
        f.write('        return default_value\n')
        f.write('    \n')
        f.write('    # Convert to appropriate type\n')
        f.write('    if var_type == "int":\n')
        f.write('        try:\n')
        f.write('            return int(user_input)\n')
        f.write('        except ValueError:\n')
        f.write('            print(f"Invalid integer, using default: {default_value}")\n')
        f.write('            return default_value\n')
        f.write('    elif var_type == "float":\n')
        f.write('        try:\n')
        f.write('            return float(user_input)\n')
        f.write('        except ValueError:\n')
        f.write('            print(f"Invalid float, using default: {default_value}")\n')
        f.write('            return default_value\n')
        f.write('    elif var_type == "bool":\n')
        f.write("        if user_input.lower() in ['true', '1', 'yes', 'y']:\n")
        f.write('            return True\n')
        f.write("        elif user_input.lower() in ['false', '0', 'no', 'n']:\n")
        f.write('            return False\n')
        f.write('        else:\n')
        f.write('            print(f"Invalid boolean, using default: {default_value}")\n')
        f.write('            return default_value\n')
        f.write('    else:\n')
        f.write('        return user_input\n\n\n')
        f.write('def main():\n')
        f.write('    config = load_config()\n')
        f.write('    \n')
        f.write('    # List available scripts\n')
        f.write('    print("=" * 60)\n')
        f.write('    print("  Simulation Manager - Interactive Script Executor")\n')
        f.write('    print("=" * 60)\n')
        f.write('    print("\\nAvailable Python scripts:")\n')
        f.write('    print()\n')
        f.write('    \n')
        f.write('    script_list = sorted(config.keys())\n')
        f.write('    for i, script_name in enumerate(script_list, 1):\n')
        f.write('        var_count = len(config[script_name])\n')
        f.write('        print(f"  {i}. {script_name} ({var_count} configurable variables)")\n')
        f.write('    \n')
        f.write('    print()\n')
        f.write('    \n')
        f.write('    # Get script selection\n')
        f.write('    while True:\n')
        f.write('        choice = input(f"Select script to run (1-{len(script_list)}) or \'q\' to quit: ").strip()\n')
        f.write("        if choice.lower() == 'q':\n")
        f.write('            print("Exiting...")\n')
        f.write('            sys.exit(0)\n')
        f.write('        \n')
        f.write('        try:\n')
        f.write('            choice_num = int(choice)\n')
        f.write('            if 1 <= choice_num <= len(script_list):\n')
        f.write('                selected_script = script_list[choice_num - 1]\n')
        f.write('                break\n')
        f.write('            else:\n')
        f.write('                print(f"Please enter a number between 1 and {len(script_list)}")\n')
        f.write('        except ValueError:\n')
        f.write('            print("Invalid input. Please enter a number or \'q\'")\n')
        f.write('    \n')
        f.write('    print()\n')
        f.write('    print(f"Selected: {selected_script}")\n')
        f.write('    print("-" * 60)\n')
        f.write('    \n')
        f.write('    # Get variable values\n')
        f.write('    script_config = config[selected_script]\n')
        f.write('    args = []\n')
        f.write('    \n')
        f.write('    if script_config:\n')
        f.write('        print("\\nConfigure variables (press Enter to use default):")\n')
        f.write('        print()\n')
        f.write('        \n')
        f.write("        for var_name, var_info in sorted(script_config.items(), key=lambda x: x[1]['line']):\n")
        f.write("            default_value = var_info['value']\n")
        f.write("            var_type = var_info['type']\n")
        f.write("            arg_flag = var_info['arg']\n")
        f.write('            \n')
        f.write('            user_value = get_user_input(f"  {var_name}", default_value, var_type)\n')
        f.write('            \n')
        f.write('            # Only add argument if different from default\n')
        f.write('            if user_value != default_value:\n')
        f.write('                args.append(arg_flag)\n')
        f.write('                args.append(str(user_value))\n')
        f.write('    \n')
        f.write('    # Execute the script\n')
        f.write('    print()\n')
        f.write('    print("-" * 60)\n')
        f.write('    print(f"Executing: {selected_script}")\n')
        f.write('    if args:\n')
        f.write("        print(f\"Arguments: {' '.join(args)}\")\n")
        f.write('    print("-" * 60)\n')
        f.write('    print()\n')
        f.write('    \n')
        f.write('    script_path = Path(__file__).parent / selected_script\n')
        f.write('    \n')
        f.write('    try:\n')
        f.write('        result = subprocess.run(\n')
        f.write('            [sys.executable, str(script_path)] + args,\n')
        f.write('            check=False\n')
        f.write('        )\n')
        f.write('        \n')
        f.write('        print()\n')
        f.write('        print("-" * 60)\n')
        f.write('        if result.returncode == 0:\n')
        f.write('            print(f"✓ {selected_script} completed successfully")\n')
        f.write('        else:\n')
        f.write('            print(f"✗ {selected_script} exited with code {result.returncode}")\n')
        f.write('        print("-" * 60)\n')
        f.write('        \n')
        f.write('    except Exception as e:\n')
        f.write('        print(f"Error executing script: {e}")\n')
        f.write('        sys.exit(1)\n\n\n')
        f.write("if __name__ == '__main__':\n")
        f.write('    main()\n')
    
    # Make it executable on Unix-like systems
    try:
        manager_path.chmod(0o755)
    except:
        pass


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
    run_parser.add_argument('name', help='Name of the project directory to run')
    
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

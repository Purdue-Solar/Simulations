"""Development tools commands: extract_and_link_fields"""

import sys
import ast
import json
from pathlib import Path


def _extract_variables_from_file(py_file):
    """Extract variables from a single Python file.
    
    Only extracts module-level variables, not variables inside functions.
    
    Args:
        py_file: Path to the Python file
        
    Returns:
        list: List of tuples (var_name, value, line_num, col_offset, is_expression)
    """
    try:
        with open(py_file, 'r', encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content, filename=py_file.name)
        
        file_vars = []
        
        # Only walk through top-level (module-level) statements
        for node in tree.body:
            if isinstance(node, ast.Assign):
                # Only process single target assignments at module level
                if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                    var_name = node.targets[0].id
                    
                    # Skip private/dunder variables
                    if var_name.startswith('_'):
                        continue
                    
                    # Extract value - only simple literals and expressions
                    value = None
                    is_expression = False
                    
                    if isinstance(node.value, ast.Constant):
                        # Simple literal
                        value = ast.literal_eval(node.value)
                    elif isinstance(node.value, (ast.List, ast.Tuple, ast.Dict)):
                        # Collection literal
                        try:
                            value = ast.literal_eval(node.value)
                        except:
                            is_expression = True
                            value = ast.unparse(node.value) if hasattr(ast, 'unparse') else None
                    elif isinstance(node.value, ast.UnaryOp) and isinstance(node.value.op, ast.USub):
                        # Negative number
                        try:
                            value = ast.literal_eval(node.value)
                        except:
                            pass
                    else:
                        # Expression
                        is_expression = True
                        value = ast.unparse(node.value) if hasattr(ast, 'unparse') else None
                    
                    if value is not None:
                        file_vars.append((
                            var_name,
                            value,
                            node.lineno,
                            node.col_offset,
                            is_expression
                        ))
        
        return file_vars
    
    except SyntaxError as e:
        print(f"  {py_file.name}: Syntax error at line {e.lineno}")
        return []
    except Exception as e:
        print(f"  {py_file.name}: Error - {e}")
        return []


def _prepare_config_data(extracted_vars):
    """Prepare configuration data for JSON format.
    
    Only includes configurable variables (non-expressions).
    
    Args:
        extracted_vars: Dictionary mapping filenames to variable lists
        
    Returns:
        dict: Configuration data formatted for manager.py (only configurable vars)
    """
    config_data = {}
    for filename, vars_list in extracted_vars.items():
        config_data[filename] = {}
        for var_name, value, line_num, _, is_expression in vars_list:
            # Skip expression variables - they cannot be configured via command line
            if is_expression:
                continue
                
            config_data[filename][var_name] = {
                'value': value,
                'type': type(value).__name__,
                'line': line_num,
                'arg': f'--{var_name}',
            }
    return config_data


def _find_insertion_point(lines):
    """Find the insertion point for argparse code (after imports, before first variable).
    
    Args:
        lines: List of file lines
        
    Returns:
        int: Line number where argparse code should be inserted
    """
    insert_line = 0
    in_docstring = False
    docstring_quote = None
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Track docstrings
        if not in_docstring:
            if stripped.startswith('"""') or stripped.startswith("'''"):
                docstring_quote = '"""' if stripped.startswith('"""') else "'''"
                if stripped.count(docstring_quote) >= 2:
                    # Single-line docstring
                    continue
                else:
                    in_docstring = True
                    continue
        else:
            if docstring_quote is not None and docstring_quote in stripped:
                in_docstring = False
                docstring_quote = None
                continue
            continue
        
        # Skip comments and empty lines
        if not stripped or stripped.startswith('#'):
            continue
        
        # Track imports
        if stripped.startswith('import ') or stripped.startswith('from '):
            insert_line = i + 1
            continue
        
        # Found first non-import statement
        break
    
    return insert_line


def _generate_argparse_code(extracted_vars):
    """Generate argparse code for command-line arguments.
    
    Args:
        extracted_vars: List of tuples (var_name, value, line_num, col_offset, is_expression)
        
    Returns:
        list: List of code lines to insert
    """
    argparse_code = [
        '\n',
        '# Auto-generated argument parsing\n',
        'import argparse\n',
        'parser = argparse.ArgumentParser(description="Configurable script")\n'
    ]
    
    for var_name, value, _, _, is_expression in extracted_vars:
        var_type = type(value).__name__
        if var_type == 'bool':
            argparse_code.append(
                f'parser.add_argument("--{var_name}", type=lambda x: x.lower() in ["true", "1", "yes", "y"], '
                f'default={value}, help="Default: {value}")\n'
            )
        elif var_type in ['int', 'float']:
            argparse_code.append(
                f'parser.add_argument("--{var_name}", type={var_type}, '
                f'default={value}, help="Default: {value}")\n'
            )
        else:
            # String or expression
            default_repr = repr(value) if not is_expression else f'"{value}"'
            argparse_code.append(
                f'parser.add_argument("--{var_name}", type=str, '
                f'default={default_repr}, help="Default: {value}")\n'
            )
    
    argparse_code.append('args = parser.parse_args()\n\n')
    return argparse_code


def _modify_file_for_argparse(py_file, extracted_vars):
    """Modify a Python file to use command-line arguments.
    
    Only modifies non-expression variables. Expression variables are left unchanged.
    
    Args:
        py_file: Path to the Python file
        extracted_vars: List of tuples (var_name, value, line_num, col_offset, is_expression)
        
    Returns:
        bool: True if modification succeeded, False otherwise
    """
    try:
        with open(py_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Filter to only configurable (non-expression) variables
        configurable_vars = [(name, val, line, col) for name, val, line, col, is_expr in extracted_vars if not is_expr]
        
        if not configurable_vars:
            return False
        
        # Parse to get AST with line numbers
        content = ''.join(lines)
        tree = ast.parse(content, filename=py_file.name)
        
        # Find all assignments to modify (only for configurable variables)
        configurable_var_names = {v[0] for v in configurable_vars}
        assignments_to_modify = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                    var_name = node.targets[0].id
                    # Only modify if it's a configurable (non-expression) variable
                    if var_name in configurable_var_names:
                        assignments_to_modify.append((var_name, node.lineno))
        
        if not assignments_to_modify:
            return False
        
        # Find insertion point
        insert_line = _find_insertion_point(lines)
        
        # Generate and insert argparse code (only for configurable variables)
        argparse_code = _generate_argparse_code([(n, v, l, c, False) for n, v, l, c in configurable_vars])
        lines[insert_line:insert_line] = argparse_code
        
        # Adjust line numbers due to insertion
        line_offset = len(argparse_code)
        
        # Modify variable assignments (only for configurable variables)
        for var_name, orig_line_num in assignments_to_modify:
            adjusted_line_num = orig_line_num + line_offset - 1  # -1 for 0-indexing
            
            if adjusted_line_num >= len(lines):
                continue
            
            original_line = lines[adjusted_line_num]
            
            # Find the assignment
            if '=' in original_line:
                indent = len(original_line) - len(original_line.lstrip())
                indent_str = ' ' * indent
                
                # Replace with args version
                lines[adjusted_line_num] = f'{indent_str}{var_name} = args.{var_name}\n'
        
        # Write modified file
        with open(py_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        return True
    
    except Exception as e:
        print(f"  ✗ Error modifying {py_file.name}: {e}")
        return False


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
        file_vars = _extract_variables_from_file(py_file)
        if file_vars:
            extracted_vars[py_file.name] = file_vars
            print(f"  {py_file.name}: {len(file_vars)} variables")
    
    if not extracted_vars:
        print("\nNo variables extracted.")
        return
    
    # Prepare configuration data for JSON format
    config_data = _prepare_config_data(extracted_vars)
    
    # Now modify source files to use command-line arguments
    print("\nModifying source files to use command-line arguments...")
    
    for py_file in python_files:
        if py_file.name not in extracted_vars:
            continue
        
        if _modify_file_for_argparse(py_file, extracted_vars[py_file.name]):
            print(f"  ✓ Modified {py_file.name}")
    
    print("\n✓ Extraction and modification complete!")
    print(f"  Total variables: {sum(len(v) for v in extracted_vars.values())}")
    print(f"\nVariables can now be set via command-line arguments:")
    for filename, vars_list in sorted(extracted_vars.items()):
        # Filter to only show configurable variables
        configurable = []
        for v in vars_list:
            if not v[4]:  # not is_expression
                configurable.append(v)
        
        if not configurable:
            continue
        print(f"\n  {filename}:")
        for var_name, value, _, _, _ in sorted(configurable, key=lambda x: x[2])[:3]:
            print(f"    --{var_name}={value}")
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
        f.write('def get_python_executable():\n')
        f.write('    """Get the Python executable, preferring virtual environment if available."""\n')
        f.write('    script_dir = Path(__file__).parent\n')
        f.write('    \n')
        f.write('    # Check for uv virtual environment (.venv/bin/python)\n')
        f.write('    venv_python = script_dir / ".venv" / "bin" / "python"\n')
        f.write('    if venv_python.exists():\n')
        f.write('        return str(venv_python)\n')
        f.write('    \n')
        f.write('    # Fallback to current Python executable\n')
        f.write('    return sys.executable\n\n\n')
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
        f.write('    python_exe = get_python_executable()\n')
        f.write('    \n')
        f.write('    try:\n')
        f.write('        result = subprocess.run(\n')
        f.write('            [python_exe, str(script_path)] + args,\n')
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

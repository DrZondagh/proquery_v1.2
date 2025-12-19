
# pycharm_error_scanner.py
# Your full working error/style scanner — drop anywhere and run

import os
import subprocess
import sys
from pathlib import Path
import pprint  # For pretty-printing issues


def scan_project(fix=False):
    project_root = Path(__file__).parent.parent  # Assumes tools/ in root
    src_dir = project_root / 'src'
    if not src_dir.exists():
        print("Error: src/ not found—run from project root.")
        sys.exit(1)

    issues = {}
    for file_path in src_dir.rglob('*.py'):
        rel_path = file_path.relative_to(project_root)
        print(f"Scanning {rel_path}...")

        # Run pylint
        try:
            result = subprocess.run(['pylint', str(file_path)], capture_output=True, text=True)
            output = result.stdout + result.stderr
            if 'No config file found' in output:
                print("Warning: No pylint config—using defaults.")
            issues[str(rel_path)] = parse_pylint_output(output)
        except FileNotFoundError:
            print("Error: pylint not installed. Run 'pip install pylint'.")
            sys.exit(1)

        if fix:
            try:
                subprocess.run(['autopep8', '--in-place', '--aggressive', str(file_path)], check=True)
                print(f"Auto-fixed style in {rel_path}.")
            except FileNotFoundError:
                print("Warning: autopep8 not installed for fixes. Run 'pip install autopep8'.")
            except subprocess.CalledProcessError:
                print(f"Failed to fix {rel_path}.")

    pprint.pprint(issues, width=120)
    if not issues:
        print("No issues found—project clean!")


def parse_pylint_output(output):
    lines = output.splitlines()
    errors = [line for line in lines if line.startswith('E:')]      # Red errors
    warnings = [line for line in lines if line.startswith('W:')]   # Yellow warnings
    conventions = [line for line in lines if line.startswith('C:')] # Style/conventions
    return {'errors (red)': errors, 'warnings (yellow)': warnings, 'conventions/other': conventions}


if __name__ == "__main__":
    fix = '--fix' in sys.argv
    scan_project(fix)
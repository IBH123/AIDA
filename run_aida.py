#!/usr/bin/env python3
"""
AIDA Launcher Script
This script ensures AIDA runs with the correct virtual environment
"""
import sys
import subprocess
import os

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

# Path to the virtual environment Python
venv_python = os.path.join(script_dir, ".venv", "Scripts", "python.exe")

# Check if virtual environment Python exists
if not os.path.exists(venv_python):
    print("Error: Virtual environment not found!")
    print(f"Expected: {venv_python}")
    print("Please run: python -m venv .venv && .venv\\Scripts\\pip install -r requirements.txt")
    sys.exit(1)

# Run AIDA with the virtual environment Python
cmd = [venv_python, "-m", "aida.cli"] + sys.argv[1:]
subprocess.run(cmd, cwd=script_dir)
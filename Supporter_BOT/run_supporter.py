#!/usr/bin/env python3
"""
Run script for Supporter Discord Bot
Place this in the Supporter-BOT folder
"""

import sys
import os

# Add the Python-Files directory to the path
python_files_dir = os.path.join(os.path.dirname(__file__), "Python_Files")
sys.path.insert(0, python_files_dir)

# Import and run the supporter bot
from supporter import run_bot

if __name__ == "__main__":
    print("🚀 Starting Supporter Bot...")
    run_bot()

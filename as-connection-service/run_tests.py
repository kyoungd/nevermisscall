#!/usr/bin/env python3
"""Test runner for as-connection-service."""

import subprocess
import sys
import os

def run_tests():
    """Run all tests with coverage."""
    # Change to the service directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Install dependencies first
    print("Installing test dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
    
    # Run tests
    print("Running tests...")
    result = subprocess.run([
        sys.executable, "-m", "pytest",
        "tests/",
        "--verbose",
        "--tb=short", 
        "--cov=src/as_connection_service",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--cov-fail-under=80"
    ])
    
    return result.returncode

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
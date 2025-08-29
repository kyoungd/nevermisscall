#!/usr/bin/env python3
"""
Test runner for as-infrastructure-service
"""

import sys
import subprocess
from pathlib import Path


def run_tests():
    """Run all unit tests."""
    print("🧪 Running as-infrastructure-service unit tests...")
    print("=" * 50)
    
    # Run pytest with coverage
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/unit/",
        "-v",
        "--tb=short",
        "--color=yes"
    ]
    
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent, check=False)
        
        if result.returncode == 0:
            print("\n✅ All tests passed!")
        else:
            print(f"\n❌ Tests failed with return code {result.returncode}")
        
        return result.returncode
        
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
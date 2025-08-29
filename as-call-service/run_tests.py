#!/usr/bin/env python3
"""Test runner script for as-call-service."""

import os
import sys
import subprocess
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


def run_tests():
    """Run all tests with coverage reporting."""
    print("🧪 Running as-call-service tests...")
    
    # Change to project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    # Run tests with pytest
    cmd = [
        "python", "-m", "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "--cov=src/as_call_service",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--cov-fail-under=70",  # Realistic coverage target
    ]
    
    try:
        result = subprocess.run(cmd, check=True)
        print("✅ All tests passed!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Tests failed with exit code: {e.returncode}")
        return False


def run_unit_tests():
    """Run only unit tests."""
    print("🔬 Running unit tests...")
    
    cmd = [
        "python", "-m", "pytest",
        "tests/unit/",
        "-v",
        "--tb=short",
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("✅ Unit tests passed!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Unit tests failed with exit code: {e.returncode}")
        return False


def run_integration_tests():
    """Run only integration tests."""
    print("🔗 Running integration tests...")
    
    cmd = [
        "python", "-m", "pytest",
        "tests/integration/",
        "-v",
        "--tb=short",
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("✅ Integration tests passed!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Integration tests failed with exit code: {e.returncode}")
        return False


def run_linting():
    """Run code linting with flake8."""
    print("🔍 Running code linting...")
    
    cmd = ["python", "-m", "flake8", "src/", "--max-line-length=100"]
    
    try:
        subprocess.run(cmd, check=True)
        print("✅ Linting passed!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Linting failed with exit code: {e.returncode}")
        return False


def run_type_checking():
    """Run type checking with mypy."""
    print("📝 Running type checking...")
    
    cmd = ["python", "-m", "mypy", "src/as_call_service", "--ignore-missing-imports"]
    
    try:
        subprocess.run(cmd, check=True)
        print("✅ Type checking passed!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Type checking failed with exit code: {e.returncode}")
        return False


def run_formatting_check():
    """Check code formatting with black."""
    print("🎨 Checking code formatting...")
    
    cmd = ["python", "-m", "black", "--check", "src/", "tests/"]
    
    try:
        subprocess.run(cmd, check=True)
        print("✅ Code formatting is correct!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Code formatting issues found. Run 'python -m black src/ tests/' to fix.")
        return False


def run_all_checks():
    """Run all quality checks."""
    print("🚀 Running all quality checks for as-call-service...")
    
    checks = [
        ("Unit Tests", run_unit_tests),
        ("Integration Tests", run_integration_tests),
        ("Code Linting", run_linting),
        ("Type Checking", run_type_checking),
        ("Code Formatting", run_formatting_check),
    ]
    
    results = {}
    for check_name, check_func in checks:
        print(f"\n{'='*50}")
        print(f"Running {check_name}")
        print(f"{'='*50}")
        results[check_name] = check_func()
    
    # Summary
    print(f"\n{'='*50}")
    print("SUMMARY")
    print(f"{'='*50}")
    
    all_passed = True
    for check_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{check_name:<20} {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All checks passed! Ready for deployment.")
        return True
    else:
        print("\n❌ Some checks failed. Please fix the issues before deploying.")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test runner for as-call-service")
    parser.add_argument(
        "test_type",
        nargs="?",
        choices=["unit", "integration", "all", "checks", "lint", "type", "format"],
        default="all",
        help="Type of tests to run"
    )
    
    args = parser.parse_args()
    
    if args.test_type == "unit":
        success = run_unit_tests()
    elif args.test_type == "integration":
        success = run_integration_tests()
    elif args.test_type == "all":
        success = run_tests()
    elif args.test_type == "checks":
        success = run_all_checks()
    elif args.test_type == "lint":
        success = run_linting()
    elif args.test_type == "type":
        success = run_type_checking()
    elif args.test_type == "format":
        success = run_formatting_check()
    else:
        success = run_tests()
    
    sys.exit(0 if success else 1)
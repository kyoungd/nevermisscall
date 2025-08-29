#!/usr/bin/env python3
"""
Test runner for AS Alerts Service.

Provides organized test execution following the three-tier testing
architecture and "honest failure over eager passing" principle.
"""

import unittest
import sys
import os
from pathlib import Path

# Add service directory and parent directory (for shared library) to Python path
service_dir = Path(__file__).parent
sys.path.insert(0, str(service_dir))
sys.path.insert(0, str(service_dir.parent))  # For shared library access


class AlertsServiceTestRunner:
    """Custom test runner for organized execution of AS Alerts Service tests."""
    
    def __init__(self):
        self.test_dir = service_dir / 'tests'
    
    def run_unit_tests(self, verbose=False):
        """Run unit tests with heavy mocking."""
        print("=" * 70)
        print("RUNNING AS ALERTS SERVICE UNIT TESTS (Heavy Mocking)")
        print("=" * 70)
        
        unit_test_dir = self.test_dir / 'unit'
        if not unit_test_dir.exists():
            print("No unit tests found - skipping")
            return True
        
        loader = unittest.TestLoader()
        suite = loader.discover(
            str(unit_test_dir),
            pattern='test_*.py',
            top_level_dir=str(self.test_dir)
        )
        
        runner = unittest.TextTestRunner(
            verbosity=2 if verbose else 1,
            stream=sys.stdout,
            descriptions=True,
            failfast=False
        )
        
        result = runner.run(suite)
        return result.wasSuccessful()
    
    def run_integration_tests(self, verbose=False):
        """Run integration tests with selective mocking."""
        print("\n" + "=" * 70)
        print("RUNNING AS ALERTS SERVICE INTEGRATION TESTS (Selective Mocking)")
        print("=" * 70)
        
        integration_dir = self.test_dir / 'integration'
        if not integration_dir.exists():
            print("No integration tests found - skipping")
            return True
        
        loader = unittest.TestLoader()
        suite = loader.discover(
            str(integration_dir),
            pattern='test_*.py',
            top_level_dir=str(self.test_dir)
        )
        
        runner = unittest.TextTestRunner(
            verbosity=2 if verbose else 1,
            stream=sys.stdout,
            descriptions=True,
            failfast=False
        )
        
        result = runner.run(suite)
        return result.wasSuccessful()
    
    def run_e2e_tests(self, verbose=False):
        """Run end-to-end tests with no mocking."""
        print("\n" + "=" * 70)
        print("RUNNING AS ALERTS SERVICE E2E TESTS (No Mocking)")
        print("=" * 70)
        
        e2e_dir = self.test_dir / 'e2e'
        if not e2e_dir.exists():
            print("No E2E tests found - skipping")
            return True
        
        loader = unittest.TestLoader()
        suite = loader.discover(
            str(e2e_dir),
            pattern='test_*.py',
            top_level_dir=str(self.test_dir)
        )
        
        runner = unittest.TextTestRunner(
            verbosity=2 if verbose else 1,
            stream=sys.stdout,
            descriptions=True,
            failfast=False
        )
        
        result = runner.run(suite)
        return result.wasSuccessful()
    
    def run_all_tests(self, verbose=False):
        """Run all test tiers in sequence."""
        print("AS Alerts Service Test Suite")
        print("Testing following 'Honest Failure Over Eager Passing' principle")
        print("")
        
        results = []
        
        # Run unit tests first (fastest feedback)
        results.append(self.run_unit_tests(verbose))
        
        # Run integration tests
        results.append(self.run_integration_tests(verbose))
        
        # Run E2E tests last (slowest)
        results.append(self.run_e2e_tests(verbose))
        
        # Summary
        print("\n" + "=" * 70)
        print("AS ALERTS SERVICE TEST SUMMARY")
        print("=" * 70)
        
        all_passed = all(results)
        print(f"Unit Tests: {'PASS' if results[0] else 'FAIL'}")
        print(f"Integration Tests: {'PASS' if results[1] else 'FAIL'}")
        print(f"E2E Tests: {'PASS' if results[2] else 'FAIL'}")
        print("")
        print(f"Overall Result: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
        
        return all_passed
    
    def run_specific_test_file(self, test_file, verbose=False):
        """Run tests from a specific test file."""
        print(f"Running tests from: {test_file}")
        print("=" * 70)
        
        # Find the test file
        test_path = None
        for root, dirs, files in os.walk(self.test_dir):
            if test_file in files:
                test_path = Path(root) / test_file
                break
        
        if not test_path:
            print(f"Test file '{test_file}' not found")
            return False
        
        # Load and run the specific test module
        loader = unittest.TestLoader()
        
        # Import the test module
        import importlib.util
        module_name = test_file.replace('.py', '')
        spec = importlib.util.spec_from_file_location(module_name, test_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Load tests from the module
        suite = loader.loadTestsFromModule(module)
        
        runner = unittest.TextTestRunner(
            verbosity=2 if verbose else 1,
            stream=sys.stdout,
            descriptions=True,
            failfast=False
        )
        
        result = runner.run(suite)
        return result.wasSuccessful()


def main():
    """Main test runner entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Run AS Alerts Service tests',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Tiers:
  unit        - Fast tests with heavy mocking
  integration - Component integration with selective mocking  
  e2e         - Full system tests with no mocking
  all         - Run all test tiers (default)

Specific Tests:
  --file      - Run tests from specific file (e.g., test_models.py)

Examples:
  python run_tests.py                           # Run all tests
  python run_tests.py unit                     # Run only unit tests
  python run_tests.py integration -v           # Run integration tests verbosely
  python run_tests.py --file test_models.py    # Run specific test file
        """
    )
    
    parser.add_argument(
        'tier',
        nargs='?',
        default='all',
        choices=['unit', 'integration', 'e2e', 'all'],
        help='Test tier to run (default: all)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose test output'
    )
    
    parser.add_argument(
        '--file',
        type=str,
        help='Run tests from specific file (e.g., test_models.py)'
    )
    
    args = parser.parse_args()
    
    runner = AlertsServiceTestRunner()
    
    # Handle specific file execution
    if args.file:
        success = runner.run_specific_test_file(args.file, args.verbose)
        sys.exit(0 if success else 1)
    
    # Handle tier execution
    if args.tier == 'unit':
        success = runner.run_unit_tests(args.verbose)
    elif args.tier == 'integration':
        success = runner.run_integration_tests(args.verbose)
    elif args.tier == 'e2e':
        success = runner.run_e2e_tests(args.verbose)
    else:  # all
        success = runner.run_all_tests(args.verbose)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
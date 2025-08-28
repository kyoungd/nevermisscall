#!/usr/bin/env python3
"""
Test runner for NeverMissCall shared library.

Provides organized test execution following the three-tier testing
architecture defined in documentation-requirement.md.
"""

import unittest
import sys
import os
from pathlib import Path

# Add shared library to Python path
shared_dir = Path(__file__).parent
sys.path.insert(0, str(shared_dir.parent))


class SharedLibraryTestRunner:
    """Custom test runner for organized execution of shared library tests."""
    
    def __init__(self):
        self.test_dir = shared_dir / 'tests'
    
    def run_unit_tests(self, verbose=False):
        """Run unit tests with heavy mocking."""
        print("=" * 70)
        print("RUNNING UNIT TESTS (Heavy Mocking)")
        print("=" * 70)
        
        loader = unittest.TestLoader()
        suite = loader.discover(
            str(self.test_dir / 'unit'),
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
        print("RUNNING INTEGRATION TESTS (Selective Mocking)")
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
        print("RUNNING E2E TESTS (No Mocking)")
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
        print("NeverMissCall Shared Library Test Suite")
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
        print("TEST SUMMARY")
        print("=" * 70)
        
        all_passed = all(results)
        print(f"Unit Tests: {'PASS' if results[0] else 'FAIL'}")
        print(f"Integration Tests: {'PASS' if results[1] else 'FAIL'}")
        print(f"E2E Tests: {'PASS' if results[2] else 'FAIL'}")
        print("")
        print(f"Overall Result: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
        
        return all_passed


def main():
    """Main test runner entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Run NeverMissCall shared library tests',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Tiers:
  unit        - Fast tests with heavy mocking
  integration - Component integration with selective mocking  
  e2e         - Full system tests with no mocking
  all         - Run all test tiers (default)

Examples:
  python run_tests.py                    # Run all tests
  python run_tests.py unit               # Run only unit tests
  python run_tests.py integration -v     # Run integration tests verbosely
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
    
    args = parser.parse_args()
    
    runner = SharedLibraryTestRunner()
    
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
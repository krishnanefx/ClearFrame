"""Test runner and configuration."""

import unittest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def run_all_tests():
    """Run all tests in the test suite."""
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def run_integration_tests():
    """Run only integration tests."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName('test_integration')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def run_state_tests():
    """Run only state management tests."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName('test_state')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run test suite')
    parser.add_argument(
        '--suite',
        choices=['all', 'integration', 'state', 'complete'],
        default='all',
        help='Test suite to run'
    )
    
    args = parser.parse_args()
    
    if args.suite == 'all':
        success = run_all_tests()
    elif args.suite == 'integration':
        success = run_integration_tests()
    elif args.suite == 'state':
        success = run_state_tests()
    elif args.suite == 'complete':
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromName('test_integration_complete')
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        success = result.wasSuccessful()
    
    sys.exit(0 if success else 1)

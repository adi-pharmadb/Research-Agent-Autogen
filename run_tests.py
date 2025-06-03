#!/usr/bin/env python3
"""
Test runner for PharmaDB Deep-Research Micro-Service

This script runs the complete test suite including:
- Unit tests for individual components
- Integration tests for the research flow
- API endpoint tests

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --unit             # Run only unit tests
    python run_tests.py --integration      # Run only integration tests
    python run_tests.py --api              # Run only API tests
    python run_tests.py --coverage         # Run with coverage report
"""
import subprocess
import sys
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"🔄 {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Run PharmaDB tests")
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration", action="store_true", help="Run only integration tests")
    parser.add_argument("--api", action="store_true", help="Run only API tests")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Base pytest command - use python3 instead of python
    base_cmd = "python3 -m pytest"
    
    if args.verbose:
        base_cmd += " -v"
    
    # Determine which tests to run
    test_patterns = []
    
    if args.unit:
        test_patterns.append("tests/test_tools.py")
    elif args.integration:
        test_patterns.append("tests/test_integration.py")
    elif args.api:
        test_patterns.append("tests/test_api.py")
    else:
        # Run all tests
        test_patterns.append("tests/")
    
    # Add coverage if requested
    if args.coverage:
        base_cmd = "python3 -m pytest --cov=app --cov-report=html --cov-report=term"
    
    # Build final command
    test_cmd = f"{base_cmd} {' '.join(test_patterns)}"
    
    print("🧪 PharmaDB Deep-Research Micro-Service Test Suite")
    print("=" * 60)
    
    # Check if tests directory exists
    if not Path("tests").exists():
        print("❌ Tests directory not found!")
        sys.exit(1)
    
    # Run the tests
    success = run_command(test_cmd, "Running Test Suite")
    
    if success:
        print("\n✅ All tests completed successfully!")
        if args.coverage:
            print("📊 Coverage report generated in htmlcov/index.html")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main() 
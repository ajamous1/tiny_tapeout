#!/usr/bin/env python3
"""
Run comprehensive test suite and generate VCD file
This script attempts to run the test using cocotb's runner
"""

import os
import sys
import subprocess

def main():
    # Check if we're in the test directory
    if not os.path.exists('tb.v'):
        print("Error: Must run from test directory")
        sys.exit(1)
    
    # Try to run using make if available
    try:
        print("Attempting to run test with make...")
        result = subprocess.run(
            ['make', '-B', 'MODULE=test_comprehensive'],
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if os.path.exists('tb_updated.vcd'):
            print("\n✅ Test completed! VCD file generated: tb_updated.vcd")
        else:
            print("\n⚠️  Test completed but VCD file not found")
    except FileNotFoundError:
        print("Error: 'make' not found. Please install make or use WSL/Git Bash.")
        print("\nAlternative: Install make via:")
        print("  - Chocolatey: choco install make")
        print("  - MSYS2: Install MSYS2 and use its make")
        print("  - WSL: Use Windows Subsystem for Linux")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error running make: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        sys.exit(1)

if __name__ == '__main__':
    main()


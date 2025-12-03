#!/usr/bin/env python3
"""
Run Emulator Script
===================
Helper script to run the Tiny Canvas emulator in different modes.

Usage:
    python run_emulator.py [mode]

Modes:
    gui      - Run standalone GUI test (no Verilog simulation)
    sim      - Run with Verilog simulation via cocotb (requires make)
    help     - Show this help message

The GUI mode is useful for testing the interface without needing
the full simulation toolchain (Icarus Verilog, cocotb, etc.)
"""

import sys
import os
import subprocess

def print_banner():
    print("=" * 60)
    print("  TINY CANVAS - Interactive Emulator")
    print("=" * 60)

def run_gui_mode():
    """Run standalone GUI without Verilog simulation."""
    print_banner()
    print("Running in GUI-only mode (no Verilog simulation)")
    print("-" * 60)
    
    # Import and run the emulator directly
    try:
        import pygame
    except ImportError:
        print("ERROR: pygame not installed!")
        print("Install with: pip install pygame")
        return 1
    
    # Change to test directory and run
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Import and run the emulator
    from interactive_emulator import main as run_emulator
    run_emulator()
    return 0

def run_sim_mode():
    """Run with Verilog simulation via cocotb."""
    print_banner()
    print("Running with Verilog RTL simulation")
    print("-" * 60)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Add iverilog to PATH if needed (Windows)
    iverilog_path = "C:\\iverilog\\bin"
    if os.path.exists(iverilog_path):
        os.environ["PATH"] = iverilog_path + os.pathsep + os.environ.get("PATH", "")
    
    # Check for required tools
    try:
        result = subprocess.run(["iverilog", "-V"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("ERROR: Icarus Verilog (iverilog) not found!")
        print("Please install Icarus Verilog to run RTL simulation.")
        print("")
        print("Download from: http://bleyer.org/icarus/")
        print("")
        print("Or try GUI-only mode: python run_emulator.py gui")
        return 1
    
    # Run simulation script
    print("Starting cocotb simulation...")
    print("This will compile and simulate the Verilog design.")
    print("-" * 60)
    
    sim_script = os.path.join(script_dir, "run_sim.py")
    result = subprocess.run([sys.executable, sim_script], cwd=script_dir)
    
    return result.returncode

def print_help():
    print(__doc__)
    print("\nKeyboard Controls:")
    print("-" * 60)
    print("  Arrow Keys  = Move cursor")
    print("  A           = Toggle RED")
    print("  S           = Toggle GREEN")  
    print("  D           = Toggle BLUE")
    print("  SPACE       = Toggle BRUSH/ERASER")
    print("  C           = Clear canvas")
    print("  ESC / Q     = Quit")
    print("")
    print("Colour Mixing:")
    print("-" * 60)
    print("  R only      → Red      (100)")
    print("  G only      → Green    (010)")
    print("  B only      → Blue     (001)")
    print("  R + G       → Yellow   (110)")
    print("  R + B       → Magenta  (101)")
    print("  G + B       → Cyan     (011)")
    print("  R + G + B   → White    (111)")
    print("  None/Eraser → Black    (000)")
    print("")
    print("I2C Protocol:")
    print("-" * 60)
    print("  3 bytes transmitted on each move:")
    print("    Byte 1: X position (0-255)")
    print("    Byte 2: Y position (0-255)")
    print("    Byte 3: Status byte")
    print("")
    print("  Status Byte [7:0]:")
    print("    [7]   = Up button pressed")
    print("    [6]   = Down button pressed")
    print("    [5]   = Left button pressed")
    print("    [4]   = Right button pressed")
    print("    [3]   = Brush mode (1=Brush, 0=Eraser)")
    print("    [2:0] = RGB colour bits")

def main():
    if len(sys.argv) < 2:
        # Default to GUI mode
        mode = "gui"
    else:
        mode = sys.argv[1].lower()
    
    if mode == "gui":
        return run_gui_mode()
    elif mode == "sim":
        return run_sim_mode()
    elif mode in ("help", "-h", "--help"):
        print_help()
        return 0
    else:
        print(f"Unknown mode: {mode}")
        print("Use 'gui', 'sim', or 'help'")
        return 1

if __name__ == "__main__":
    sys.exit(main())


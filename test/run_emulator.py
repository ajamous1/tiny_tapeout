#!/usr/bin/env python3
"""
Tiny Canvas GUI Emulator
========================
Run the interactive canvas emulator with controller interface.

Usage:
    python run_emulator.py [gui|help]

For RTL simulation with live signals, use:
    python run_stickman.py
"""

import sys
import os

def main():
    print("=" * 60)
    print("  TINY CANVAS - Interactive Emulator")
    print("=" * 60)
    
    if len(sys.argv) > 1 and sys.argv[1].lower() in ("help", "-h", "--help"):
        print(__doc__)
        print("\nKeyboard Controls:")
        print("  Arrow Keys  = Move cursor")
        print("  A           = Toggle RED")
        print("  S           = Toggle GREEN")  
        print("  D           = Toggle BLUE")
        print("  SPACE       = Toggle BRUSH/ERASER")
        print("  C           = Clear canvas")
        print("  ESC / Q     = Quit")
        print("\nColour Mixing:")
        print("  R=Red, G=Green, B=Blue")
        print("  R+G=Yellow, R+B=Magenta, G+B=Cyan, R+G+B=White")
        return 0
    
    print("Running GUI emulator...")
    print("-" * 60)
    
    try:
        import pygame
    except ImportError:
        print("ERROR: pygame not installed!")
        print("Install with: pip install pygame")
        return 1
    
    # Run the emulator
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    from interactive_emulator import main as run_emulator
    run_emulator()
    return 0

if __name__ == "__main__":
    sys.exit(main())


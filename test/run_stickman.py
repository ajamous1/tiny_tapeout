#!/usr/bin/env python3
"""Run the Stickman demo with live signal waveforms."""

import os, sys, subprocess, shutil

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    src_dir = os.path.join(project_root, "src")
    sim_build = os.path.join(script_dir, "sim_build")
    
    print("=" * 60)
    print("  STICKMAN DEMO - Verilog RTL + Live Signals")
    print("=" * 60)
    
    # Add iverilog to PATH
    if os.path.exists("C:\\iverilog\\bin"):
        os.environ["PATH"] = "C:\\iverilog\\bin" + os.pathsep + os.environ.get("PATH", "")
    
    if not shutil.which("iverilog"):
        print("ERROR: Icarus Verilog not found!")
        return 1
    
    # Compile
    os.makedirs(sim_build, exist_ok=True)
    vvp_file = os.path.join(sim_build, "sim.vvp")
    
    sources = [os.path.join(src_dir, f) for f in 
               ["project.v", "counter.v", "i2c_slave.v", "position.v", "gamepad_pmod.v", "colour.v"]]
    sources.append(os.path.join(script_dir, "tb.v"))
    
    print("Compiling Verilog...")
    result = subprocess.run(["iverilog", "-o", vvp_file, "-g2012", f"-I{src_dir}", "-s", "tb"] + sources,
                          capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Compile error: {result.stderr}")
        return 1
    print("  Compiled!")
    
    # Run
    print("\nStarting demo - watch the signals update in real-time!")
    print("-" * 60)
    
    import cocotb
    libs_dir = os.path.join(os.path.dirname(cocotb.__file__), "libs")
    
    os.chdir(script_dir)
    env = os.environ.copy()
    env["MODULE"] = "test_stickman"
    env["TOPLEVEL"] = "tb"
    env["TOPLEVEL_LANG"] = "verilog"
    
    subprocess.run(["vvp", "-M", libs_dir, "-m", "cocotbvpi_icarus", vvp_file], env=env)
    
    print("-" * 60)
    print("Demo complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main())


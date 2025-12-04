# Run the debug demo with comprehensive logging
# This script compiles and runs debug_demo.py through cocotb
# The debug demo includes extensive signal tracing to diagnose issues

$ErrorActionPreference = "Stop"

Write-Host "Running Debug Demo with Comprehensive Logging..." -ForegroundColor Cyan
Write-Host "This will drive the Verilog RTL with extensive signal tracing" -ForegroundColor Yellow
Write-Host ""

# Create directory if needed
New-Item -ItemType Directory -Force -Path sim_build/rtl | Out-Null

Write-Host "Compiling testbench..." -ForegroundColor Cyan

# Compile with iverilog
$srcFiles = @(
    "../src/project.v",
    "../src/counter.v",
    "../src/i2c_slave.v",
    "../src/position.v",
    "../src/gamepad_pmod.v",
    "../src/colour.v",
    "../src/brush_settings.v",
    "../src/fill_mode.v",
    "../src/fill_draw.v",
    "../src/packet_generator.v",
    "../src/undo_redo.v",
    "tb.v"
)

$compileCmd = "iverilog -o sim_build/rtl/sim.vvp -D COCOTB_SIM=1 -s tb -g2012 -I../src " + ($srcFiles -join " ")

Write-Host "Running: $compileCmd" -ForegroundColor Yellow
Invoke-Expression $compileCmd

if ($LASTEXITCODE -ne 0) {
    Write-Host "Compilation failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`nRunning debug demo with cocotb (MODULE=debug_demo)..." -ForegroundColor Cyan

# Set up cocotb environment
$env:MODULE = "debug_demo"
$env:TOPLEVEL = "tb"
$env:COCOTB_REDUCED_LOG_FMT = "1"

# Get cocotb path
$cocotbPath = python -c "import cocotb; import os; print(os.path.dirname(cocotb.__file__))" 2>$null
$vpiLibPath = "$cocotbPath\libs"
$vpiLib = "$vpiLibPath\cocotbvpi_icarus.vpl"

if (-not (Test-Path $vpiLib)) {
    Write-Host "Error: Could not find cocotb VPI library at $vpiLib" -ForegroundColor Red
    Write-Host "Please ensure cocotb is installed: pip install cocotb" -ForegroundColor Yellow
    exit 1
}

# Run vvp with cocotb
$runCmd = "vvp -M `"$vpiLibPath`" -m cocotbvpi_icarus sim_build/rtl/sim.vvp"

Write-Host "Starting pygame window and Verilog simulation..." -ForegroundColor Green
Write-Host "Running: $runCmd" -ForegroundColor Yellow
Write-Host ""
Write-Host "The debug demo will:" -ForegroundColor Cyan
Write-Host "  - Test button presses (A for Red)" -ForegroundColor White
Write-Host "  - Test movement and painting" -ForegroundColor White
Write-Host "  - Log all key signals for debugging" -ForegroundColor White
Write-Host "  - Display results in pygame window" -ForegroundColor White
Write-Host ""

Invoke-Expression $runCmd

if (Test-Path "tb_updated.vcd") {
    Write-Host "`n✅ Debug demo completed! VCD file generated: tb_updated.vcd" -ForegroundColor Green
    Write-Host "You can view waveforms with: gtkwave tb_updated.vcd" -ForegroundColor Cyan
} else {
    Write-Host "`n⚠️  Debug demo completed but VCD file not found" -ForegroundColor Yellow
}


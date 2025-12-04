# Manual test runner for Windows (when make is not available)
# This script manually compiles and runs the cocotb test
# Usage: .\run_test_manual.ps1 [MODULE]
#   MODULE defaults to "test_comprehensive"
#   Examples:
#     .\run_test_manual.ps1 test_autopilot_full
#     .\run_test_manual.ps1 test_comprehensive
#     .\run_test_manual.ps1 debug_demo

param(
    [string]$MODULE = "test_comprehensive"
)

# Handle if user passes "MODULE=test_name" format
if ($MODULE -match "^MODULE=(.+)$") {
    $MODULE = $matches[1]
    Write-Host "Extracted module name: $MODULE" -ForegroundColor Cyan
}

$ErrorActionPreference = "Stop"

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

Write-Host "`nRunning test with cocotb (MODULE=$MODULE)..." -ForegroundColor Cyan

# Set up cocotb environment
$env:MODULE = $MODULE
$env:TOPLEVEL = "tb"
$env:COCOTB_REDUCED_LOG_FMT = "1"

# Get cocotb VPI library path
$cocotbPath = python -c "import cocotb; import os; print(os.path.dirname(cocotb.__file__))" 2>$null
$vpiLibPath = "$cocotbPath\libs"
$vpiLib = "$vpiLibPath\cocotbvpi_icarus.vpl"

if (-not (Test-Path $vpiLib)) {
    Write-Host "Error: Could not find cocotb VPI library at $vpiLib" -ForegroundColor Red
    Write-Host "Please install make or use WSL/Git Bash to run tests" -ForegroundColor Yellow
    exit 1
}

# Run vvp with cocotb
$runCmd = "vvp -M `"$vpiLibPath`" -m cocotbvpi_icarus sim_build/rtl/sim.vvp"

Write-Host "Running: $runCmd" -ForegroundColor Yellow
Invoke-Expression $runCmd

if (Test-Path "tb_updated.vcd") {
    Write-Host "`n✅ Test completed! VCD file generated: tb_updated.vcd" -ForegroundColor Green
    Write-Host "You can view it with: gtkwave tb_updated.vcd" -ForegroundColor Cyan
} else {
    Write-Host "`n⚠️  Test completed but VCD file not found" -ForegroundColor Yellow
}


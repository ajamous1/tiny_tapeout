# Run comprehensive tests and generate waveforms
# This script runs the test suite and ensures VCD files are generated

$ErrorActionPreference = "Stop"

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "Running Comprehensive Test Suite with Waveforms" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# Create directory if needed
New-Item -ItemType Directory -Force -Path sim_build/rtl | Out-Null

Write-Host "Compiling testbench with VCD dumping enabled..." -ForegroundColor Cyan

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

Write-Host "`nRunning comprehensive test suite..." -ForegroundColor Cyan

# Set up cocotb environment
$env:MODULE = "test_comprehensive"
$env:TOPLEVEL = "tb"
$env:COCOTB_REDUCED_LOG_FMT = "1"

# Get cocotb VPI library path
$cocotbPath = python -c "import cocotb; import os; print(os.path.dirname(cocotb.__file__))" 2>$null
$vpiLibPath = "$cocotbPath\libs"
$vpiLib = "$vpiLibPath\cocotbvpi_icarus.vpl"

if (-not (Test-Path $vpiLib)) {
    Write-Host "Error: Could not find cocotb VPI library at $vpiLib" -ForegroundColor Red
    Write-Host "Please install cocotb: pip install cocotb" -ForegroundColor Yellow
    exit 1
}

# Run vvp with cocotb
$runCmd = "vvp -M `"$vpiLibPath`" -m cocotbvpi_icarus sim_build/rtl/sim.vvp"

Write-Host "Running: $runCmd" -ForegroundColor Yellow
Write-Host ""

Invoke-Expression $runCmd

$testExitCode = $LASTEXITCODE

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "Test Results" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

if ($testExitCode -eq 0) {
    Write-Host "✅ All tests PASSED!" -ForegroundColor Green
} else {
    Write-Host "❌ Some tests FAILED (exit code: $testExitCode)" -ForegroundColor Red
}

# Check for VCD file
if (Test-Path "tb_updated.vcd") {
    $vcdSize = (Get-Item "tb_updated.vcd").Length / 1MB
    Write-Host ""
    Write-Host "✅ VCD waveform file generated: tb_updated.vcd" -ForegroundColor Green
    Write-Host "   File size: $([math]::Round($vcdSize, 2)) MB" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To view waveforms:" -ForegroundColor Cyan
    Write-Host "  1. Install GTKWave: https://gtkwave.sourceforge.net/" -ForegroundColor White
    Write-Host "  2. Open with: gtkwave tb_updated.vcd" -ForegroundColor White
    Write-Host ""
    Write-Host "  Or use Surfer: https://github.com/potentialventures/surfer" -ForegroundColor White
    Write-Host "  Open with: surfer tb_updated.vcd" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "⚠️  VCD file not found. Check testbench compilation." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Test Summary:" -ForegroundColor Cyan
Write-Host "  - Comprehensive test suite covers:" -ForegroundColor White
Write-Host "    • Reset functionality" -ForegroundColor Gray
Write-Host "    • Color mixing (RGB channels)" -ForegroundColor Gray
Write-Host "    • Brush size adjustment" -ForegroundColor Gray
Write-Host "    • Symmetry modes" -ForegroundColor Gray
Write-Host "    • Position tracking" -ForegroundColor Gray
Write-Host "    • Fill rectangle mode" -ForegroundColor Gray
Write-Host "    • Undo/Redo functionality" -ForegroundColor Gray
Write-Host "    • I2C communication" -ForegroundColor Gray
Write-Host "    • Paint enable logic" -ForegroundColor Gray
Write-Host "    • Integration test" -ForegroundColor Gray

exit $testExitCode


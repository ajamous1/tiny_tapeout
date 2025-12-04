# Testbench for Tiny Canvas

This directory contains comprehensive test suites for the Tiny Canvas project using [cocotb](https://docs.cocotb.org/en/stable/).

## Test Files

- **`test.py`**: Basic I2C communication test
- **`test_comprehensive.py`**: Comprehensive test suite covering all features:
  - Color mixing (A, Y, X buttons)
  - Brush size (L, R buttons)
  - Symmetry modes (Start button)
  - Position tracking (D-pad)
  - Fill rectangle mode (Select, B buttons)
  - Undo/Redo (L+R, Select+Start combos)
  - I2C communication
  - Paint enable logic
  - Integration test

## How to run

### Run basic I2C test:
```sh
make -B
```

### Run comprehensive test suite:
```sh
make -B MODULE=test_comprehensive
```

### Run gate-level simulation:
First harden your project and copy `../runs/wokwi/results/final/verilog/gl/tt_um_example.v` to `gate_level_netlist.v`.

Then run:
```sh
make -B GATES=yes MODULE=test_comprehensive
```

## How to view the VCD file

Using GTKWave
```sh
gtkwave tb.vcd tb.gtkw
```

Using Surfer
```sh
surfer tb.vcd
```

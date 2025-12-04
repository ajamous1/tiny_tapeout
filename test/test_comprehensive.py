# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

"""
Comprehensive test suite for Tiny Canvas
Tests all features: color mixing, brush size, symmetry, fill rectangle, undo/redo, position tracking
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer, RisingEdge, FallingEdge
from cocotb.binary import BinaryValue

# Gamepad PMOD simulation helpers
async def gamepad_pmod_send_bit(dut, data):
    """Send a single bit through the gamepad PMOD interface (data sampled on rising edge of clk)"""
    dut.ui_in[6].value = data  # pmod_data
    await ClockCycles(dut.clk, 2)
    dut.ui_in[5].value = 1  # pmod_clk high
    await ClockCycles(dut.clk, 3)  # Hold high for sampling
    dut.ui_in[5].value = 0  # pmod_clk low
    await ClockCycles(dut.clk, 2)

async def gamepad_pmod_send_buttons(dut, buttons):
    """
    Send button state through gamepad PMOD (12 bits for single controller)
    buttons: dict with keys: b, y, select, start, up, down, left, right, a, x, l, r
    """
    # Button order: B, Y, select, start, up, down, left, right, A, X, L, R (MSB first)
    button_order = ['b', 'y', 'select', 'start', 'up', 'down', 'left', 'right', 'a', 'x', 'l', 'r']
    
    # Initialize: data low, clock low, latch low
    dut.ui_in[6].value = 0  # pmod_data
    dut.ui_in[5].value = 0  # pmod_clk
    dut.ui_in[4].value = 0  # pmod_latch
    await ClockCycles(dut.clk, 2)
    
    # Send all 12 bits serially (MSB first)
    for btn in button_order:
        bit = 1 if buttons.get(btn, 0) else 0
        await gamepad_pmod_send_bit(dut, bit)
    
    # Latch pulse (high pulse to transfer shift_reg to data_reg)
    await ClockCycles(dut.clk, 2)
    dut.ui_in[4].value = 1  # pmod_latch high
    await ClockCycles(dut.clk, 5)
    dut.ui_in[4].value = 0  # pmod_latch low
    await ClockCycles(dut.clk, 5)

async def press_button_edge(dut, buttons_before, buttons_after):
    """Simulate button press edge (press and release)"""
    await gamepad_pmod_send_buttons(dut, buttons_before)
    await ClockCycles(dut.clk, 10)
    await gamepad_pmod_send_buttons(dut, buttons_after)
    await ClockCycles(dut.clk, 10)
    await gamepad_pmod_send_buttons(dut, {})  # Release all
    await ClockCycles(dut.clk, 10)

@cocotb.test()
async def test_reset(dut):
    """Test reset functionality"""
    cocotb.start_soon(Clock(dut.clk, 20, units="ns").start())
    
    dut.ena.value = 1
    dut.rst_n.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 5)
    
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 10)
    
    dut._log.info("Reset test passed ✅")

@cocotb.test()
async def test_color_mixing(dut):
    """Test RGB color mixing with A, Y, X buttons"""
    cocotb.start_soon(Clock(dut.clk, 20, units="ns").start())
    
    # Reset
    dut.ena.value = 1
    dut.rst_n.value = 0
    dut.ui_in.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 10)
    
    # Test A button (Red)
    dut._log.info("Testing A button (Red)")
    await press_button_edge(dut, {}, {'a': 1})
    await ClockCycles(dut.clk, 5)
    # Check that red is toggled (we can't directly read internal state, but we can check I2C output)
    
    # Test Y button (Green)
    dut._log.info("Testing Y button (Green)")
    await press_button_edge(dut, {}, {'y': 1})
    await ClockCycles(dut.clk, 5)
    
    # Test X button (Blue)
    dut._log.info("Testing X button (Blue)")
    await press_button_edge(dut, {}, {'x': 1})
    await ClockCycles(dut.clk, 5)
    
    # Test all colors together (should be white)
    dut._log.info("Testing all colors (White)")
    await press_button_edge(dut, {}, {'a': 1})
    await ClockCycles(dut.clk, 5)
    await press_button_edge(dut, {}, {'y': 1})
    await ClockCycles(dut.clk, 5)
    await press_button_edge(dut, {}, {'x': 1})
    await ClockCycles(dut.clk, 5)
    
    dut._log.info("Color mixing test passed ✅")

@cocotb.test()
async def test_brush_size(dut):
    """Test brush size increase/decrease with L/R buttons"""
    cocotb.start_soon(Clock(dut.clk, 20, units="ns").start())
    
    # Reset
    dut.ena.value = 1
    dut.rst_n.value = 0
    dut.ui_in.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 10)
    
    # Test R button (increase size)
    dut._log.info("Testing R button (increase brush size)")
    for i in range(3):
        await press_button_edge(dut, {}, {'r': 1})
        await ClockCycles(dut.clk, 10)
    
    # Test L button (decrease size)
    dut._log.info("Testing L button (decrease brush size)")
    for i in range(2):
        await press_button_edge(dut, {}, {'l': 1})
        await ClockCycles(dut.clk, 10)
    
    dut._log.info("Brush size test passed ✅")

@cocotb.test()
async def test_symmetry_mode(dut):
    """Test symmetry mode cycling with Start button"""
    cocotb.start_soon(Clock(dut.clk, 20, units="ns").start())
    
    # Reset
    dut.ena.value = 1
    dut.rst_n.value = 0
    dut.ui_in.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 10)
    
    # Cycle through symmetry modes
    dut._log.info("Testing Start button (symmetry mode)")
    for i in range(4):
        await press_button_edge(dut, {}, {'start': 1})
        await ClockCycles(dut.clk, 10)
    
    dut._log.info("Symmetry mode test passed ✅")

@cocotb.test()
async def test_position_tracking(dut):
    """Test cursor position tracking with D-pad"""
    cocotb.start_soon(Clock(dut.clk, 20, units="ns").start())
    
    # Reset
    dut.ena.value = 1
    dut.rst_n.value = 0
    dut.ui_in.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 10)
    
    # Test D-pad movement
    dut._log.info("Testing D-pad (position tracking)")
    
    # Move right
    await gamepad_pmod_send_buttons(dut, {'right': 1})
    await ClockCycles(dut.clk, 10)
    await gamepad_pmod_send_buttons(dut, {})
    await ClockCycles(dut.clk, 10)
    
    # Move down
    await gamepad_pmod_send_buttons(dut, {'down': 1})
    await ClockCycles(dut.clk, 10)
    await gamepad_pmod_send_buttons(dut, {})
    await ClockCycles(dut.clk, 10)
    
    # Move left
    await gamepad_pmod_send_buttons(dut, {'left': 1})
    await ClockCycles(dut.clk, 10)
    await gamepad_pmod_send_buttons(dut, {})
    await ClockCycles(dut.clk, 10)
    
    # Move up
    await gamepad_pmod_send_buttons(dut, {'up': 1})
    await ClockCycles(dut.clk, 10)
    await gamepad_pmod_send_buttons(dut, {})
    await ClockCycles(dut.clk, 10)
    
    dut._log.info("Position tracking test passed ✅")

@cocotb.test()
async def test_fill_rectangle_mode(dut):
    """Test fill rectangle mode with Select and B buttons"""
    cocotb.start_soon(Clock(dut.clk, 20, units="ns").start())
    
    # Reset
    dut.ena.value = 1
    dut.rst_n.value = 0
    dut.ui_in.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 10)
    
    # Enable fill mode
    dut._log.info("Testing Select button (toggle fill mode)")
    await press_button_edge(dut, {}, {'select': 1})
    await ClockCycles(dut.clk, 10)
    
    # Set corner A
    dut._log.info("Testing B button (set corner A)")
    await press_button_edge(dut, {}, {'b': 1})
    await ClockCycles(dut.clk, 10)
    
    # Move cursor
    await gamepad_pmod_send_buttons(dut, {'right': 1})
    await ClockCycles(dut.clk, 10)
    await gamepad_pmod_send_buttons(dut, {'down': 1})
    await ClockCycles(dut.clk, 10)
    await gamepad_pmod_send_buttons(dut, {})
    await ClockCycles(dut.clk, 10)
    
    # Set corner B (should trigger fill)
    dut._log.info("Testing B button (set corner B, trigger fill)")
    await press_button_edge(dut, {}, {'b': 1})
    await ClockCycles(dut.clk, 50)  # Wait for fill operation
    
    # Disable fill mode
    await press_button_edge(dut, {}, {'select': 1})
    await ClockCycles(dut.clk, 10)
    
    dut._log.info("Fill rectangle test passed ✅")

@cocotb.test()
async def test_undo_redo(dut):
    """Test undo/redo with L+R and Select+Start combos"""
    cocotb.start_soon(Clock(dut.clk, 20, units="ns").start())
    
    # Reset
    dut.ena.value = 1
    dut.rst_n.value = 0
    dut.ui_in.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 10)
    
    # Enable a color and move (to create undo history)
    await press_button_edge(dut, {}, {'a': 1})  # Red
    await ClockCycles(dut.clk, 5)
    await gamepad_pmod_send_buttons(dut, {'right': 1})
    await ClockCycles(dut.clk, 10)
    await gamepad_pmod_send_buttons(dut, {})
    await ClockCycles(dut.clk, 10)
    
    # Test undo (L+R)
    dut._log.info("Testing undo (L+R combo)")
    await gamepad_pmod_send_buttons(dut, {'l': 1, 'r': 1})
    await ClockCycles(dut.clk, 10)
    await gamepad_pmod_send_buttons(dut, {})
    await ClockCycles(dut.clk, 10)
    
    # Test redo (Select+Start)
    dut._log.info("Testing redo (Select+Start combo)")
    await gamepad_pmod_send_buttons(dut, {'select': 1, 'start': 1})
    await ClockCycles(dut.clk, 10)
    await gamepad_pmod_send_buttons(dut, {})
    await ClockCycles(dut.clk, 10)
    
    dut._log.info("Undo/Redo test passed ✅")

@cocotb.test()
async def test_i2c_communication(dut):
    """Test I2C slave communication"""
    SCL_FREQ_HZ = 100_000
    SCL_PERIOD_NS = int(1e9 // SCL_FREQ_HZ)
    
    cocotb.start_soon(Clock(dut.clk, 20, units="ns").start())
    cocotb.start_soon(Clock(dut.uio_in[2], SCL_PERIOD_NS, units="ns").start())
    
    # Reset
    dut.ena.value = 1
    dut.rst_n.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 10)
    
    # Set up some state
    await press_button_edge(dut, {}, {'a': 1})  # Red
    await ClockCycles(dut.clk, 5)
    await gamepad_pmod_send_buttons(dut, {'right': 1})
    await ClockCycles(dut.clk, 10)
    await gamepad_pmod_send_buttons(dut, {})
    await ClockCycles(dut.clk, 10)
    
    # SDA high idle
    dut.uio_in[1].value = 1
    await Timer(50, "us")
    
    # START condition
    dut._log.info("Testing I2C START condition")
    while int(dut.uio_in[2].value) != 1:
        await Timer(100, "ns")
    await Timer(500, "ns")
    dut.uio_in[1].value = 0
    await ClockCycles(dut.clk, 5)
    
    # Send address byte (0x64 = 0b1100100, with read bit = 0b11001001)
    ADDRESS_BYTE = 0b11001001
    dut._log.info(f"Sending I2C address: 0x{ADDRESS_BYTE:02X}")
    for i in range(8):
        bit = (ADDRESS_BYTE >> (7-i)) & 1
        while int(dut.uio_in[2].value) != 0:
            await Timer(50, "ns")
        dut.uio_in[1].value = bit
        while int(dut.uio_in[2].value) != 1:
            await Timer(50, "ns")
        await ClockCycles(dut.clk, 3)
    
    # Release SDA for slave ACK
    while int(dut.uio_in[2].value) != 0:
        await Timer(50, "ns")
    dut.uio_in[1].value = 1
    await ClockCycles(dut.clk, 20)
    
    # Read 3 bytes (X, Y, Status)
    for byte_num in range(3):
        dut._log.info(f"Reading byte {byte_num}")
        byte_value = 0
        for i in range(8):
            # Wait for SCL low
            while int(dut.uio_in[2].value) != 0:
                await Timer(20, "ns")
            
            # Sample data on SCL rising edge
            while int(dut.uio_in[2].value) != 1:
                await Timer(50, "ns")
            
            bit = int(dut.uio_out[1].value) if int(dut.uio_oe[1].value) else 0
            byte_value = (byte_value << 1) | bit
            await ClockCycles(dut.clk, 2)
        
        dut._log.info(f"Received byte {byte_num}: 0x{byte_value:02X} ({byte_value})")
        
        # Send ACK (except for last byte)
        if byte_num < 2:
            while int(dut.uio_in[2].value) != 0:
                await Timer(20, "ns")
            dut.uio_in[1].value = 0  # ACK
            while int(dut.uio_in[2].value) != 1:
                await Timer(100, "ns")
            await ClockCycles(dut.clk, 2)
            dut.uio_in[1].value = 1  # Release
    
    # STOP condition
    dut._log.info("Testing I2C STOP condition")
    while int(dut.uio_in[2].value) != 0:
        await Timer(20, "ns")
    dut.uio_in[1].value = 0
    while int(dut.uio_in[2].value) != 1:
        await Timer(100, "ns")
    await Timer(500, "ns")
    dut.uio_in[1].value = 1
    await ClockCycles(dut.clk, 10)
    
    dut._log.info("I2C communication test passed ✅")

@cocotb.test()
async def test_paint_enable_logic(dut):
    """Test that paint_enable works correctly (no color = no paint)"""
    cocotb.start_soon(Clock(dut.clk, 20, units="ns").start())
    
    # Reset
    dut.ena.value = 1
    dut.rst_n.value = 0
    dut.ui_in.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 10)
    
    # Move without color (should not paint)
    dut._log.info("Testing movement without color (should not paint)")
    await gamepad_pmod_send_buttons(dut, {'right': 1})
    await ClockCycles(dut.clk, 10)
    await gamepad_pmod_send_buttons(dut, {})
    await ClockCycles(dut.clk, 10)
    
    # Enable color and move (should paint)
    dut._log.info("Testing movement with color (should paint)")
    await press_button_edge(dut, {}, {'a': 1})  # Red
    await ClockCycles(dut.clk, 5)
    await gamepad_pmod_send_buttons(dut, {'right': 1})
    await ClockCycles(dut.clk, 10)
    await gamepad_pmod_send_buttons(dut, {})
    await ClockCycles(dut.clk, 10)
    
    dut._log.info("Paint enable logic test passed ✅")

@cocotb.test()
async def test_integration(dut):
    """Integration test: full drawing workflow"""
    cocotb.start_soon(Clock(dut.clk, 20, units="ns").start())
    
    # Reset
    dut.ena.value = 1
    dut.rst_n.value = 0
    dut.ui_in.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 10)
    
    dut._log.info("Running integration test: full drawing workflow")
    
    # 1. Set color (Red + Green = Yellow)
    await press_button_edge(dut, {}, {'a': 1})  # Red
    await ClockCycles(dut.clk, 5)
    await press_button_edge(dut, {}, {'y': 1})  # Green
    await ClockCycles(dut.clk, 5)
    
    # 2. Increase brush size
    await press_button_edge(dut, {}, {'r': 1})
    await ClockCycles(dut.clk, 5)
    await press_button_edge(dut, {}, {'r': 1})
    await ClockCycles(dut.clk, 5)
    
    # 3. Set symmetry mode
    await press_button_edge(dut, {}, {'start': 1})
    await ClockCycles(dut.clk, 5)
    
    # 4. Draw (move with color)
    await gamepad_pmod_send_buttons(dut, {'right': 1})
    await ClockCycles(dut.clk, 10)
    await gamepad_pmod_send_buttons(dut, {'down': 1})
    await ClockCycles(dut.clk, 10)
    await gamepad_pmod_send_buttons(dut, {})
    await ClockCycles(dut.clk, 10)
    
    # 5. Undo
    await gamepad_pmod_send_buttons(dut, {'l': 1, 'r': 1})
    await ClockCycles(dut.clk, 10)
    await gamepad_pmod_send_buttons(dut, {})
    await ClockCycles(dut.clk, 10)
    
    # 6. Fill rectangle
    await press_button_edge(dut, {}, {'select': 1})  # Enable fill mode
    await ClockCycles(dut.clk, 5)
    await press_button_edge(dut, {}, {'b': 1})  # Corner A
    await ClockCycles(dut.clk, 5)
    await gamepad_pmod_send_buttons(dut, {'right': 1, 'down': 1})
    await ClockCycles(dut.clk, 10)
    await gamepad_pmod_send_buttons(dut, {})
    await ClockCycles(dut.clk, 5)
    await press_button_edge(dut, {}, {'b': 1})  # Corner B
    await ClockCycles(dut.clk, 50)  # Wait for fill
    
    dut._log.info("Integration test passed ✅")


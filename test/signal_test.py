"""
signal_test.py - Discover correct signal paths and verify functionality
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer

BUTTON_ORDER = ['b', 'y', 'select', 'start', 'up', 'down', 'left', 'right', 'a', 'x', 'l', 'r']


async def send_pmod_bit(dut, bit):
    """Send a single bit via PMOD protocol"""
    current = dut.ui_in.value.integer
    if bit:
        current |= (1 << 6)
    else:
        current &= ~(1 << 6)
    dut.ui_in.value = current
    
    # Clock low
    dut.ui_in.value = dut.ui_in.value.integer & ~(1 << 5)
    await ClockCycles(dut.clk, 2)
    
    # Clock high
    dut.ui_in.value = dut.ui_in.value.integer | (1 << 5)
    await ClockCycles(dut.clk, 2)
    
    # Clock low
    dut.ui_in.value = dut.ui_in.value.integer & ~(1 << 5)
    await ClockCycles(dut.clk, 1)


async def send_buttons(dut, buttons):
    """Send button state via PMOD protocol"""
    dut.ui_in.value = dut.ui_in.value.integer & 0x0F
    await ClockCycles(dut.clk, 2)
    
    for btn in BUTTON_ORDER:
        bit = 1 if buttons.get(btn, 0) else 0
        await send_pmod_bit(dut, bit)
    
    await ClockCycles(dut.clk, 2)
    dut.ui_in.value = dut.ui_in.value.integer | (1 << 4)
    await ClockCycles(dut.clk, 4)
    dut.ui_in.value = dut.ui_in.value.integer & ~(1 << 4)
    await ClockCycles(dut.clk, 4)


def try_read(dut, path):
    """Try to read a signal, return (value, success)"""
    try:
        parts = path.split('.')
        obj = dut
        for p in parts:
            obj = getattr(obj, p)
        return (int(obj.value), True)
    except Exception as e:
        return (None, False)


@cocotb.test()
async def test_signal_discovery(dut):
    """Discover correct signal paths"""
    
    cocotb.start_soon(Clock(dut.clk, 20, units="ns").start())
    
    # Reset
    dut.ena.value = 1
    dut.rst_n.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 20)
    
    dut._log.info("="*70)
    dut._log.info("SIGNAL PATH DISCOVERY")
    dut._log.info("="*70)
    
    # List of signal paths to try
    signal_paths = [
        # Top-level wires in project.v
        "user_project.sw_red",
        "user_project.sw_green", 
        "user_project.sw_blue",
        "user_project.brush_mode",
        "user_project.colour_out",
        "user_project.paint_enable",
        "user_project.x_pos",
        "user_project.y_pos",
        "user_project.movement",
        "user_project.movement_edge",
        "user_project.freehand_trigger",
        "user_project.pixel_trigger",
        "user_project.fill_active_wire",
        
        # Gamepad signals
        "user_project.gp_a",
        "user_project.gp_y",
        "user_project.gp_x",
        "user_project.gp_up",
        "user_project.gp_down",
        "user_project.gp_left",
        "user_project.gp_right",
        "user_project.gp_is_present",
        
        # Module instances
        "user_project.colour_inst.colour_out",
        "user_project.colour_inst.paint_enable",
        "user_project.colour_inst.sw_red",
        "user_project.pos_inst.x_pos",
        "user_project.pos_inst.y_pos",
        "user_project.pkt_inst.valid",
        "user_project.pkt_inst.busy",
        "user_project.pkt_inst.x_out",
        "user_project.pkt_inst.y_out",
        "user_project.pkt_inst.trigger",
        "user_project.brush_inst.brush_size",
        "user_project.brush_inst.symmetry_mode",
        "user_project.fill_mode_inst.fill_active",
        "user_project.gamepad_inst.is_present",
        "user_project.gamepad_inst.a",
    ]
    
    dut._log.info("\nChecking signal paths...")
    valid_paths = []
    
    for path in signal_paths:
        val, ok = try_read(dut, path)
        if ok:
            dut._log.info(f"  [OK] {path} = {val}")
            valid_paths.append(path)
        else:
            dut._log.info(f"  [--] {path} (not found)")
    
    dut._log.info(f"\nFound {len(valid_paths)} valid signal paths")
    
    # =========================================================================
    # Test gamepad input
    # =========================================================================
    dut._log.info("\n" + "="*70)
    dut._log.info("TESTING GAMEPAD INPUT")
    dut._log.info("="*70)
    
    # Try to find gamepad output signals
    gamepad_paths = [p for p in valid_paths if 'gp_' in p or 'gamepad' in p]
    dut._log.info(f"Gamepad-related paths: {gamepad_paths}")
    
    # Send A button
    dut._log.info("\nSending A button press...")
    await send_buttons(dut, {'a': 1})
    await ClockCycles(dut.clk, 10)
    
    dut._log.info("Values after A press:")
    for path in valid_paths:
        val, _ = try_read(dut, path)
        if 'red' in path.lower() or 'gp_a' in path.lower() or 'colour' in path.lower() or 'paint' in path.lower():
            dut._log.info(f"  {path} = {val}")
    
    # Release A
    await send_buttons(dut, {})
    await ClockCycles(dut.clk, 10)
    
    dut._log.info("\nValues after A release:")
    for path in valid_paths:
        val, _ = try_read(dut, path)
        if 'red' in path.lower() or 'gp_a' in path.lower() or 'colour' in path.lower() or 'paint' in path.lower():
            dut._log.info(f"  {path} = {val}")
    
    # =========================================================================
    # Test movement
    # =========================================================================
    dut._log.info("\n" + "="*70)
    dut._log.info("TESTING MOVEMENT")
    dut._log.info("="*70)
    
    dut._log.info("\nSending RIGHT button...")
    await send_buttons(dut, {'right': 1})
    await ClockCycles(dut.clk, 10)
    
    dut._log.info("Values during RIGHT press:")
    for path in valid_paths:
        val, _ = try_read(dut, path)
        if 'pos' in path.lower() or 'movement' in path.lower() or 'trigger' in path.lower() or 'gp_right' in path.lower():
            dut._log.info(f"  {path} = {val}")
    
    # Release
    await send_buttons(dut, {})
    await ClockCycles(dut.clk, 10)
    
    dut._log.info("\nValues after RIGHT release:")
    for path in valid_paths:
        val, _ = try_read(dut, path)
        if 'pos' in path.lower() or 'x_pos' in path or 'y_pos' in path:
            dut._log.info(f"  {path} = {val}")
    
    # =========================================================================
    # Full painting test
    # =========================================================================
    dut._log.info("\n" + "="*70)
    dut._log.info("FULL PAINTING TEST")
    dut._log.info("="*70)
    
    # Step 1: Enable Red
    dut._log.info("\nStep 1: Toggle Red ON (press A)")
    await send_buttons(dut, {})
    await ClockCycles(dut.clk, 5)
    await send_buttons(dut, {'a': 1})
    await ClockCycles(dut.clk, 5)
    await send_buttons(dut, {})
    await ClockCycles(dut.clk, 10)
    
    sw_red, _ = try_read(dut, 'user_project.sw_red')
    colour_out, _ = try_read(dut, 'user_project.colour_out')
    paint_enable, _ = try_read(dut, 'user_project.paint_enable')
    dut._log.info(f"  sw_red={sw_red}, colour_out={colour_out}, paint_enable={paint_enable}")
    
    if paint_enable != 1:
        dut._log.error("paint_enable should be 1!")
        
        # Debug: check colour module inputs
        dut._log.info("\nDebugging colour module:")
        for sig in ['user_project.colour_inst.sw_red', 
                    'user_project.colour_inst.sw_green',
                    'user_project.colour_inst.sw_blue',
                    'user_project.colour_inst.brush_mode']:
            val, ok = try_read(dut, sig)
            dut._log.info(f"  {sig} = {val} (found={ok})")
    
    # Step 2: Move RIGHT
    dut._log.info("\nStep 2: Move RIGHT (should paint)")
    pixels_found = 0
    
    for i in range(5):
        await send_buttons(dut, {'right': 1})
        
        for _ in range(20):
            pkt_valid, _ = try_read(dut, 'user_project.pkt_inst.valid')
            
            if pkt_valid:
                pkt_x, _ = try_read(dut, 'user_project.pkt_inst.x_out')
                pkt_y, _ = try_read(dut, 'user_project.pkt_inst.y_out')
                dut._log.info(f"  PIXEL at ({pkt_x}, {pkt_y})!")
                pixels_found += 1
            
            await ClockCycles(dut.clk, 1)
        
        await send_buttons(dut, {})
        await ClockCycles(dut.clk, 5)
    
    dut._log.info(f"\nTotal pixels found: {pixels_found}")
    
    if pixels_found == 0:
        dut._log.error("NO PIXELS GENERATED!")
        
        # Check all relevant signals
        dut._log.info("\nDiagnostic dump:")
        diagnostic_signals = [
            'user_project.movement',
            'user_project.paint_enable', 
            'user_project.fill_active_wire',
            'user_project.freehand_trigger',
            'user_project.pixel_trigger',
            'user_project.pkt_inst.trigger',
            'user_project.pkt_inst.busy',
        ]
        for sig in diagnostic_signals:
            val, ok = try_read(dut, sig)
            dut._log.info(f"  {sig} = {val}")
    else:
        dut._log.info("SUCCESS! Pixels were generated.")
    
    dut._log.info("\n" + "="*70)
    dut._log.info("TEST COMPLETE")
    dut._log.info("="*70)
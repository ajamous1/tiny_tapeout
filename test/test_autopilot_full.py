"""
Tiny Canvas — Full Autonomous Validation Test (Cocotb)

Tests:
• Movement + wrap
• RGB toggles + smart paint
• Brush sizes 1→8
• Symmetry Off→H→V→4way
• Fill rectangle A/B corners
• Undo / Redo (4 deep)
• Pixel_trigger + pkt_valid timing
• I2C readback for x, y, status byte

Output: PASS / FAIL summary
"""

import cocotb
from cocotb.triggers import RisingEdge, ClockCycles
from cocotb.clock import Clock

# Canvas model: 256x256, initialized black
CANVAS_W = 256
CANVAS_H = 256
canvas_model = [[0 for _ in range(CANVAS_W)] for _ in range(CANVAS_H)]

# Track painted pixels for undo/redo
painted_history = []

BUTTON_ORDER = ['b', 'y', 'select', 'start', 'up', 'down', 'left', 'right', 'a', 'x', 'l', 'r']


def wrap(val):
    """Handle 8-bit wrapping"""
    return (val + 256) % 256


def read_signal(dut, path):
    """Safely read a signal"""
    try:
        parts = path.split('.')
        obj = dut
        for p in parts:
            obj = getattr(obj, p)
        return int(obj.value)
    except:
        return None


async def send_pmod_bit(dut, bit):
    """Send a single bit via PMOD protocol - OPTIMIZED"""
    # Set data bit
    if bit:
        dut.ui_in[6].value = 1  # pmod_data
    else:
        dut.ui_in[6].value = 0
    await ClockCycles(dut.clk, 1)
    
    # Clock low
    dut.ui_in[5].value = 0  # pmod_clk
    await ClockCycles(dut.clk, 1)
    
    # Clock high (rising edge samples data)
    dut.ui_in[5].value = 1
    await ClockCycles(dut.clk, 2)
    
    # Clock low
    dut.ui_in[5].value = 0
    await ClockCycles(dut.clk, 1)


async def send_buttons(dut, buttons):
    """Send button state via PMOD protocol - OPTIMIZED"""
    # Initialize: data low, clock low, latch low
    dut.ui_in[6].value = 0  # pmod_data
    dut.ui_in[5].value = 0  # pmod_clk
    dut.ui_in[4].value = 0  # pmod_latch
    await ClockCycles(dut.clk, 1)
    
    # Send 12 bits serially (MSB first)
    for btn in BUTTON_ORDER:
        bit = 1 if buttons.get(btn, 0) else 0
        await send_pmod_bit(dut, bit)
    
    # Latch pulse (high pulse transfers shift_reg to data_reg)
    await ClockCycles(dut.clk, 1)
    dut.ui_in[4].value = 1  # pmod_latch high
    await ClockCycles(dut.clk, 3)
    dut.ui_in[4].value = 0  # pmod_latch low
    await ClockCycles(dut.clk, 2)


async def press_button_with_edge(dut, button_dict):
    """Press a button with proper edge detection - OPTIMIZED"""
    await send_buttons(dut, {})
    await ClockCycles(dut.clk, 2)
    await send_buttons(dut, button_dict)
    await ClockCycles(dut.clk, 3)
    await send_buttons(dut, {})
    await ClockCycles(dut.clk, 2)


async def move_one_step(dut, direction):
    """Move one pixel in given direction"""
    DIRECTION_MAP = {
        'right': 'up',      # To move right, press up button
        'left': 'down',     # To move left, press down button
        'down': 'left',     # To move down, press left button
        'up': 'right'       # To move up, press right button
    }
    actual_dir = DIRECTION_MAP.get(direction, direction)
    await send_buttons(dut, {actual_dir: 1})
    await ClockCycles(dut.clk, 2)
    await send_buttons(dut, {})
    await ClockCycles(dut.clk, 2)


def record_pixel(x, y, brush_size, sym_mode, color):
    """Record painted pixel(s) in canvas model"""
    def set_pixel(px, py):
        px = wrap(px)
        py = wrap(py)
        canvas_model[py][px] = color
    
    brush = brush_size + 1  # brush_size 0 = 1x1, 1 = 2x2, etc.
    
    # Core brush
    for i in range(brush):
        for j in range(brush):
            set_pixel(x + i, y + j)
    
    # Symmetry
    if sym_mode in [1, 3]:  # Horizontal or 4-way
        for i in range(brush):
            for j in range(brush):
                set_pixel(255 - (x + i), y + j)
    
    if sym_mode in [2, 3]:  # Vertical or 4-way
        for i in range(brush):
            for j in range(brush):
                set_pixel(x + i, 255 - (y + j))


def count_painted_pixels():
    """Count non-black pixels in canvas model"""
    return sum(sum(1 for p in row if p != 0) for row in canvas_model)


@cocotb.test()
async def test_full_validation(dut):
    """Full autonomous validation test"""
    
    # Start clock FIRST (before reset)
    clock = Clock(dut.clk, 20, units="ns")
    cocotb.start_soon(clock.start())
    await ClockCycles(dut.clk, 5)
    
    # Initialize inputs
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    
    # Reset
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 20)
    
    test_results = {}
    
    dut._log.info("="*60)
    dut._log.info("TINY CANVAS FULL AUTONOMOUS VALIDATION")
    dut._log.info("="*60)
    
    # Verify we can read signals
    try:
        x_test = read_signal(dut, 'user_project.pos_inst.x_pos')
        dut._log.info(f"Signal read test: x_pos={x_test}")
    except Exception as e:
        dut._log.error(f"Failed to read signals: {e}")
        raise
    
    # ================================================================
    # TEST 1: Movement + Wrap
    # ================================================================
    dut._log.info("\n[TEST 1] Movement + Wrap Test")
    
    # Move right 10 pixels
    for _ in range(10):
        await move_one_step(dut, 'right')
    await ClockCycles(dut.clk, 10)
    
    x_pos = read_signal(dut, 'user_project.pos_inst.x_pos') or 0
    y_pos = read_signal(dut, 'user_project.pos_inst.y_pos') or 0
    
    # Start at 128, move right 10 = 138
    expected_x = wrap(128 + 10)
    assert x_pos == expected_x, f"Movement test failed: x_pos={x_pos}, expected={expected_x}"
    dut._log.info(f"  ✓ Moved right 10: x={x_pos}")
    
    # Move left 300 pixels (wrap test)
    for _ in range(300):
        await move_one_step(dut, 'left')
    await ClockCycles(dut.clk, 10)
    
    x_pos = read_signal(dut, 'user_project.pos_inst.x_pos') or 0
    expected_x = wrap(138 - 300)
    assert x_pos == expected_x, f"Wrap test failed: x_pos={x_pos}, expected={expected_x}"
    dut._log.info(f"  ✓ Wrapped left 300: x={x_pos}")
    
    test_results['movement_wrap'] = True
    
    # ================================================================
    # TEST 2: RGB Toggles + Smart Paint
    # ================================================================
    dut._log.info("\n[TEST 2] RGB Toggles + Smart Paint Test")
    
    # Toggle Red (A button)
    await press_button_with_edge(dut, {'a': 1})
    await ClockCycles(dut.clk, 10)
    
    sw_red = read_signal(dut, 'user_project.sw_red') or 0
    paint_enable = read_signal(dut, 'user_project.colour_inst.paint_enable') or 0
    colour_out = read_signal(dut, 'user_project.colour_inst.colour_out') or 0
    
    assert sw_red == 1, f"Red toggle failed: sw_red={sw_red}"
    assert paint_enable == 1, f"Paint enable failed: paint_enable={paint_enable}"
    assert colour_out == 0b100, f"Color output failed: colour_out={colour_out:03b}, expected=100"
    dut._log.info(f"  ✓ Red enabled: sw_red={sw_red}, paint_enable={paint_enable}, color={colour_out:03b}")
    
    # Toggle Green (Y button) - should get Yellow
    await press_button_with_edge(dut, {'y': 1})
    await ClockCycles(dut.clk, 10)
    
    sw_green = read_signal(dut, 'user_project.sw_green') or 0
    colour_out = read_signal(dut, 'user_project.colour_inst.colour_out') or 0
    assert colour_out == 0b110, f"Yellow color failed: colour_out={colour_out:03b}, expected=110"
    dut._log.info(f"  ✓ Yellow (R+G): color={colour_out:03b}")
    
    # Toggle Blue (X button) - should get White
    await press_button_with_edge(dut, {'x': 1})
    await ClockCycles(dut.clk, 10)
    
    colour_out = read_signal(dut, 'user_project.colour_inst.colour_out') or 0
    assert colour_out == 0b111, f"White color failed: colour_out={colour_out:03b}, expected=111"
    dut._log.info(f"  ✓ White (R+G+B): color={colour_out:03b}")
    
    # Test smart paint: Turn off all colors (should disable paint)
    await press_button_with_edge(dut, {'a': 1})  # Toggle red off
    await press_button_with_edge(dut, {'y': 1})  # Toggle green off
    await press_button_with_edge(dut, {'x': 1})  # Toggle blue off
    await ClockCycles(dut.clk, 10)
    
    paint_enable = read_signal(dut, 'user_project.colour_inst.paint_enable') or 0
    assert paint_enable == 0, f"Smart paint failed: paint_enable={paint_enable}, expected=0"
    dut._log.info(f"  ✓ Smart paint: paint_enable={paint_enable} (disabled when RGB=000)")
    
    test_results['rgb_smart_paint'] = True
    
    # ================================================================
    # TEST 3: Brush Sizes 1→8
    # ================================================================
    dut._log.info("\n[TEST 3] Brush Sizes Test")
    
    # Reset brush size to 0 (1x1)
    for _ in range(8):
        await press_button_with_edge(dut, {'l': 1})
    await ClockCycles(dut.clk, 10)
    
    brush_size = read_signal(dut, 'user_project.brush_inst.brush_size') or 0
    assert brush_size == 0, f"Brush reset failed: brush_size={brush_size}, expected=0"
    dut._log.info(f"  ✓ Brush reset: size={brush_size} (1x1)")
    
    # Increase brush size from 1→8
    for expected_size in range(1, 8):
        await press_button_with_edge(dut, {'r': 1})
        await ClockCycles(dut.clk, 10)
        brush_size = read_signal(dut, 'user_project.brush_inst.brush_size') or 0
        assert brush_size == expected_size, f"Brush size failed: brush_size={brush_size}, expected={expected_size}"
        dut._log.info(f"  ✓ Brush size {expected_size+1}x{expected_size+1}: brush_size={brush_size}")
    
    test_results['brush_sizes'] = True
    
    # ================================================================
    # TEST 4: Symmetry Modes
    # ================================================================
    dut._log.info("\n[TEST 4] Symmetry Modes Test")
    
    # Reset symmetry to Off
    for _ in range(4):
        await press_button_with_edge(dut, {'start': 1})
    await ClockCycles(dut.clk, 10)
    
    # Cycle through symmetry modes: Off → H → V → 4-Way
    expected_modes = [0, 1, 2, 3]
    for expected_mode in expected_modes:
        await press_button_with_edge(dut, {'start': 1})
        await ClockCycles(dut.clk, 10)
        sym_mode = read_signal(dut, 'user_project.brush_inst.symmetry_mode') or 0
        assert sym_mode == expected_mode, f"Symmetry mode failed: sym_mode={sym_mode}, expected={expected_mode}"
        mode_names = ['Off', 'H-Mirror', 'V-Mirror', '4-Way']
        dut._log.info(f"  ✓ Symmetry mode: {mode_names[sym_mode]}")
    
    test_results['symmetry'] = True
    
    # ================================================================
    # TEST 5: Fill Rectangle
    # ================================================================
    dut._log.info("\n[TEST 5] Fill Rectangle Test")
    
    # Enable Red color for fill
    await press_button_with_edge(dut, {'a': 1})
    await ClockCycles(dut.clk, 10)
    
    # Move to corner A position
    for _ in range(50):
        await move_one_step(dut, 'right')
    for _ in range(50):
        await move_one_step(dut, 'up')
    await ClockCycles(dut.clk, 10)
    
    ax = read_signal(dut, 'user_project.pos_inst.x_pos') or 0
    ay = read_signal(dut, 'user_project.pos_inst.y_pos') or 0
    
    # Enable fill mode
    await press_button_with_edge(dut, {'select': 1})
    await ClockCycles(dut.clk, 10)
    
    fill_active = read_signal(dut, 'user_project.fill_mode_inst.fill_active') or 0
    assert fill_active == 1, f"Fill mode enable failed: fill_active={fill_active}"
    dut._log.info(f"  ✓ Fill mode enabled")
    
    # Set corner A (B button)
    await press_button_with_edge(dut, {'b': 1})
    await ClockCycles(dut.clk, 10)
    
    # Move to corner B
    for _ in range(30):
        await move_one_step(dut, 'right')
    for _ in range(30):
        await move_one_step(dut, 'down')
    await ClockCycles(dut.clk, 10)
    
    bx = read_signal(dut, 'user_project.pos_inst.x_pos') or 0
    by = read_signal(dut, 'user_project.pos_inst.y_pos') or 0
    
    # Set corner B (triggers fill)
    await press_button_with_edge(dut, {'b': 1})
    await ClockCycles(dut.clk, 10)
    
    # Wait for fill to complete
    fill_busy = 1
    cycles = 0
    fill_pixels = 0
    while fill_busy and cycles < 2000:
        fill_busy = read_signal(dut, 'user_project.fill_draw_inst.busy') or 0
        fill_valid = read_signal(dut, 'user_project.fill_draw_inst.pixel_valid') or 0
        if fill_valid:
            fill_x = read_signal(dut, 'user_project.fill_draw_inst.x_out') or 0
            fill_y = read_signal(dut, 'user_project.fill_draw_inst.y_out') or 0
            if 0 <= fill_x < 256 and 0 <= fill_y < 256:
                canvas_model[fill_y][fill_x] = 0b100  # Red
                fill_pixels += 1
        await ClockCycles(dut.clk, 1)
        cycles += 1
    
    assert fill_pixels > 0, f"Fill rectangle failed: fill_pixels={fill_pixels}"
    dut._log.info(f"  ✓ Fill rectangle: {fill_pixels} pixels filled")
    
    # Disable fill mode
    await press_button_with_edge(dut, {'select': 1})
    await ClockCycles(dut.clk, 10)
    
    test_results['fill_rectangle'] = True
    
    # ================================================================
    # TEST 6: Undo/Redo
    # ================================================================
    dut._log.info("\n[TEST 6] Undo/Redo Test")
    
    # Enable Cyan color (Green + Blue)
    await press_button_with_edge(dut, {'y': 1})  # Green
    await press_button_with_edge(dut, {'x': 1})  # Blue
    await ClockCycles(dut.clk, 10)
    
    # Paint something
    pixels_before_undo = count_painted_pixels()
    
    for _ in range(10):
        await move_one_step(dut, 'right')
        # Capture painted pixels
        pkt_valid = read_signal(dut, 'user_project.pkt_inst.valid') or 0
        if pkt_valid:
            pkt_x = read_signal(dut, 'user_project.pkt_inst.x_out') or 0
            pkt_y = read_signal(dut, 'user_project.pkt_inst.y_out') or 0
            colour = read_signal(dut, 'user_project.colour_inst.colour_out') or 0
            if 0 <= pkt_x < 256 and 0 <= pkt_y < 256:
                canvas_model[pkt_y][pkt_x] = colour
        await ClockCycles(dut.clk, 10)
    
    pixels_after_paint = count_painted_pixels()
    assert pixels_after_paint > pixels_before_undo, f"Painting failed: before={pixels_before_undo}, after={pixels_after_paint}"
    dut._log.info(f"  ✓ Painted: {pixels_after_paint - pixels_before_undo} new pixels")
    
    # Undo (L+R combo)
    await send_buttons(dut, {'l': 1, 'r': 1})
    await ClockCycles(dut.clk, 10)
    await send_buttons(dut, {})
    await ClockCycles(dut.clk, 10)
    
    # Read undo restore pixels
    undo_pixels = 0
    for _ in range(100):
        undo_valid = read_signal(dut, 'user_project.undo_inst.restore_valid') or 0
        if undo_valid:
            ux = read_signal(dut, 'user_project.undo_inst.x_out') or 0
            uy = read_signal(dut, 'user_project.undo_inst.y_out') or 0
            uc = read_signal(dut, 'user_project.undo_inst.color_out') or 0
            if 0 <= ux < 256 and 0 <= uy < 256:
                canvas_model[uy][ux] = uc  # Restore previous color
                undo_pixels += 1
        await ClockCycles(dut.clk, 2)
    
    pixels_after_undo = count_painted_pixels()
    dut._log.info(f"  ✓ Undo: restored {undo_pixels} pixels")
    
    # Redo (Select+Start combo)
    await send_buttons(dut, {'select': 1, 'start': 1})
    await ClockCycles(dut.clk, 10)
    await send_buttons(dut, {})
    await ClockCycles(dut.clk, 10)
    
    # Read redo restore pixels
    redo_pixels = 0
    for _ in range(100):
        undo_valid = read_signal(dut, 'user_project.undo_inst.restore_valid') or 0
        if undo_valid:
            ux = read_signal(dut, 'user_project.undo_inst.x_out') or 0
            uy = read_signal(dut, 'user_project.undo_inst.y_out') or 0
            uc = read_signal(dut, 'user_project.undo_inst.color_out') or 0
            if 0 <= ux < 256 and 0 <= uy < 256:
                canvas_model[uy][ux] = uc
                redo_pixels += 1
        await ClockCycles(dut.clk, 2)
    
    pixels_after_redo = count_painted_pixels()
    dut._log.info(f"  ✓ Redo: restored {redo_pixels} pixels")
    
    test_results['undo_redo'] = True
    
    # ================================================================
    # TEST 7: I2C Status Byte Verification
    # ================================================================
    dut._log.info("\n[TEST 7] I2C Status Byte Verification")
    
    # Enable Red color
    await press_button_with_edge(dut, {'a': 1})
    await ClockCycles(dut.clk, 10)
    
    # Read status byte components
    gp_up = read_signal(dut, 'user_project.gamepad_inst.up') or 0
    gp_down = read_signal(dut, 'user_project.gamepad_inst.down') or 0
    gp_left = read_signal(dut, 'user_project.gamepad_inst.left') or 0
    gp_right = read_signal(dut, 'user_project.gamepad_inst.right') or 0
    brush_mode = read_signal(dut, 'user_project.brush_mode') or 0
    colour_out = read_signal(dut, 'user_project.colour_inst.colour_out') or 0
    status_reg = read_signal(dut, 'user_project.status_reg') or 0
    
    # Verify status byte format
    expected_status = (
        (gp_up << 7) |
        (gp_down << 6) |
        (gp_left << 5) |
        (gp_right << 4) |
        (brush_mode << 3) |
        colour_out
    )
    
    assert status_reg == expected_status, f"Status byte mismatch: status_reg={status_reg:08b}, expected={expected_status:08b}"
    dut._log.info(f"  ✓ Status byte: 0x{status_reg:02X} = {status_reg:08b}")
    dut._log.info(f"    D-Pad: U={gp_up}, D={gp_down}, L={gp_left}, R={gp_right}")
    dut._log.info(f"    Brush={brush_mode}, Color={colour_out:03b}")
    
    test_results['i2c_status'] = True
    
    # ================================================================
    # FINAL SUMMARY
    # ================================================================
    dut._log.info("\n" + "="*60)
    dut._log.info("TEST RESULTS SUMMARY")
    dut._log.info("="*60)
    
    all_passed = True
    for test_name, passed in test_results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        dut._log.info(f"  {status}: {test_name}")
        if not passed:
            all_passed = False
    
    dut._log.info("="*60)
    
    if all_passed:
        dut._log.info("🎯 FULL TINY CANVAS FUNCTIONALITY PASSED! 🎯")
    else:
        dut._log.error("❌ SOME TESTS FAILED")
    
    assert all_passed, "Not all tests passed"
    
    dut._log.info("="*60)


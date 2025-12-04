"""
demo_features.py - Interactive Demo for Tiny Canvas Verilog RTL

This script drives the Verilog RTL via cocotb, simulating gamepad button presses
and displaying pixel outputs in real-time using Pygame.

Features demonstrated:
1. Brush Sizes (1x1 to 8x8)
2. Color Mixing (RGB → 8 colors)
3. Symmetry Modes (Off, H-Mirror, V-Mirror, 4-Way)
4. Fill Rectangle Mode
5. Undo/Redo Functionality

Usage:
    make -B MODULE=demo_features
    
Or manually:
    iverilog -o sim_build/rtl/sim.vvp -D COCOTB_SIM=1 -s tb -g2012 -I../src ../src/*.v tb.v
    vvp -M "<cocotb_libs_path>" -m cocotbvpi_icarus sim_build/rtl/sim.vvp MODULE=demo_features
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer, RisingEdge
import threading
import queue

# Try to import pygame, provide helpful error if not available
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("WARNING: pygame not available. Install with: pip install pygame")

# =============================================================================
# Constants
# =============================================================================

# Color mapping: 3-bit color code → RGB tuple
COLORS = {
    0b000: (0, 0, 0),       # Black (no color)
    0b001: (0, 0, 255),     # Blue
    0b010: (0, 255, 0),     # Green
    0b011: (0, 255, 255),   # Cyan (G+B)
    0b100: (255, 0, 0),     # Red
    0b101: (255, 0, 255),   # Magenta (R+B)
    0b110: (255, 255, 0),   # Yellow (R+G)
    0b111: (255, 255, 255)  # White (R+G+B)
}

# Canvas dimensions
CANVAS_WIDTH = 256
CANVAS_HEIGHT = 256

# Button order for PMOD protocol (MSB first)
BUTTON_ORDER = ['b', 'y', 'select', 'start', 'up', 'down', 'left', 'right', 'a', 'x', 'l', 'r']

# =============================================================================
# Pygame State and Thread
# =============================================================================

# Shared state between cocotb and pygame threads
pygame_state = {
    'canvas': [[0] * CANVAS_WIDTH for _ in range(CANVAS_HEIGHT)],
    'cursor_x': 128,
    'cursor_y': 128,
    'status': 'Initializing...',
    'info': '',
    'brush_size': 1,
    'symmetry_mode': 'Off',
    'color_code': 0,
    'fill_mode': False,
    'running': True,
    'update_queue': queue.Queue()
}


def pygame_thread():
    """Run pygame display in a separate thread"""
    if not PYGAME_AVAILABLE:
        print("Pygame not available, running in headless mode")
        while pygame_state['running']:
            # Process updates from queue silently
            try:
                while True:
                    update = pygame_state['update_queue'].get_nowait()
                    if update['type'] == 'pixel':
                        x, y, color = update['x'], update['y'], update['color']
                        if 0 <= x < CANVAS_WIDTH and 0 <= y < CANVAS_HEIGHT:
                            pygame_state['canvas'][y][x] = color
                    elif update['type'] == 'cursor':
                        pygame_state['cursor_x'] = update['x']
                        pygame_state['cursor_y'] = update['y']
            except queue.Empty:
                pass
            import time
            time.sleep(0.016)  # ~60fps equivalent
        return
    
    pygame.init()
    screen = pygame.display.set_mode((900, 650))
    pygame.display.set_caption("Tiny Canvas Demo - Verilog RTL Driven")
    font = pygame.font.Font(None, 28)
    small_font = pygame.font.Font(None, 22)
    clock = pygame.time.Clock()
    
    while pygame_state['running']:
        # Handle pygame events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame_state['running'] = False
                return
        
        # Process updates from queue
        try:
            while True:
                update = pygame_state['update_queue'].get_nowait()
                if update['type'] == 'pixel':
                    x, y, color = update['x'], update['y'], update['color']
                    if 0 <= x < CANVAS_WIDTH and 0 <= y < CANVAS_HEIGHT:
                        pygame_state['canvas'][y][x] = color
                elif update['type'] == 'cursor':
                    pygame_state['cursor_x'] = update['x']
                    pygame_state['cursor_y'] = update['y']
                elif update['type'] == 'status':
                    pygame_state['status'] = update['text']
                elif update['type'] == 'info':
                    pygame_state['info'] = update['text']
                elif update['type'] == 'brush_size':
                    pygame_state['brush_size'] = update['size']
                elif update['type'] == 'symmetry':
                    pygame_state['symmetry_mode'] = update['mode']
                elif update['type'] == 'color':
                    pygame_state['color_code'] = update['code']
                elif update['type'] == 'fill_mode':
                    pygame_state['fill_mode'] = update['active']
        except queue.Empty:
            pass
        
        # Clear screen with dark background
        screen.fill((25, 28, 35))
        
        # Draw canvas border
        pygame.draw.rect(screen, (60, 65, 75), (18, 48, 516, 516), 2)
        
        # Draw canvas
        surf = pygame.Surface((CANVAS_WIDTH, CANVAS_HEIGHT))
        for row in range(CANVAS_HEIGHT):
            for col in range(CANVAS_WIDTH):
                # Flip Y-axis for display (0,0 at bottom-left)
                surf.set_at((col, CANVAS_HEIGHT - 1 - row), COLORS[pygame_state['canvas'][row][col]])
        
        # Scale canvas to 512x512 and blit
        scaled_surf = pygame.transform.scale(surf, (512, 512))
        screen.blit(scaled_surf, (20, 50))
        
        # Draw cursor crosshair
        cx = 20 + pygame_state['cursor_x'] * 2
        cy = 50 + (CANVAS_HEIGHT - 1 - pygame_state['cursor_y']) * 2
        brush_display_size = pygame_state['brush_size'] * 2
        
        # Yellow cursor box
        pygame.draw.rect(screen, (255, 255, 0), 
                        (cx - brush_display_size // 2, cy - brush_display_size // 2, 
                         brush_display_size, brush_display_size), 2)
        
        # Crosshair lines
        pygame.draw.line(screen, (255, 255, 0), (cx - 8, cy), (cx - brush_display_size // 2 - 2, cy), 1)
        pygame.draw.line(screen, (255, 255, 0), (cx + brush_display_size // 2 + 2, cy), (cx + 8, cy), 1)
        pygame.draw.line(screen, (255, 255, 0), (cx, cy - 8), (cx, cy - brush_display_size // 2 - 2), 1)
        pygame.draw.line(screen, (255, 255, 0), (cx, cy + brush_display_size // 2 + 2), (cx, cy + 8), 1)
        
        # Draw status panel
        panel_x = 550
        panel_y = 50
        
        # Title
        title = font.render("Tiny Canvas Demo", True, (255, 200, 80))
        screen.blit(title, (panel_x, panel_y))
        
        # Current status
        status_text = font.render(pygame_state['status'], True, (100, 255, 100))
        screen.blit(status_text, (panel_x, panel_y + 40))
        
        # Info text
        if pygame_state['info']:
            info_text = small_font.render(pygame_state['info'], True, (180, 180, 180))
            screen.blit(info_text, (panel_x, panel_y + 70))
        
        # Current settings
        settings_y = panel_y + 110
        
        # Position
        pos_text = small_font.render(f"Position: ({pygame_state['cursor_x']}, {pygame_state['cursor_y']})", True, (200, 200, 200))
        screen.blit(pos_text, (panel_x, settings_y))
        
        # Brush size
        brush_text = small_font.render(f"Brush Size: {pygame_state['brush_size']}x{pygame_state['brush_size']}", True, (200, 200, 200))
        screen.blit(brush_text, (panel_x, settings_y + 25))
        
        # Symmetry mode
        sym_text = small_font.render(f"Symmetry: {pygame_state['symmetry_mode']}", True, (200, 200, 200))
        screen.blit(sym_text, (panel_x, settings_y + 50))
        
        # Current color
        color_code = pygame_state['color_code']
        color_rgb = COLORS.get(color_code, (0, 0, 0))
        color_names = ['Black', 'Blue', 'Green', 'Cyan', 'Red', 'Magenta', 'Yellow', 'White']
        color_name = color_names[color_code] if 0 <= color_code < 8 else 'Unknown'
        
        color_label = small_font.render(f"Color: {color_name}", True, (200, 200, 200))
        screen.blit(color_label, (panel_x, settings_y + 75))
        
        # Color swatch
        pygame.draw.rect(screen, color_rgb, (panel_x + 150, settings_y + 73, 20, 20))
        pygame.draw.rect(screen, (100, 100, 100), (panel_x + 150, settings_y + 73, 20, 20), 1)
        
        # Fill mode
        fill_text = small_font.render(f"Fill Mode: {'ON' if pygame_state['fill_mode'] else 'OFF'}", True, 
                                      (100, 255, 100) if pygame_state['fill_mode'] else (200, 200, 200))
        screen.blit(fill_text, (panel_x, settings_y + 100))
        
        # Controls legend
        legend_y = settings_y + 150
        legend_title = small_font.render("Controls (Gamepad):", True, (255, 200, 80))
        screen.blit(legend_title, (panel_x, legend_y))
        
        controls = [
            "A: Toggle Red",
            "Y: Toggle Green", 
            "X: Toggle Blue",
            "D-Pad: Move cursor",
            "L/R: Brush size -/+",
            "Start: Cycle symmetry",
            "Select: Toggle fill mode",
            "B: Set fill corner",
            "L+R: Undo",
            "Select+Start: Redo"
        ]
        
        for i, ctrl in enumerate(controls):
            ctrl_text = small_font.render(ctrl, True, (150, 150, 150))
            screen.blit(ctrl_text, (panel_x, legend_y + 25 + i * 20))
        
        pygame.display.flip()
        clock.tick(60)
    
    pygame.quit()


# =============================================================================
# Gamepad PMOD Protocol Functions
# =============================================================================

async def gamepad_pmod_send_bit(dut, data):
    """Send a single bit through PMOD interface
    
    Protocol:
    - Set data on pmod_data (ui_in[6])
    - Clock low, wait, clock high (rising edge captures), wait, clock low
    """
    dut.ui_in.value = (dut.ui_in.value.integer & ~(1 << 6)) | (data << 6)  # pmod_data = ui_in[6]
    dut.ui_in.value = dut.ui_in.value.integer & ~(1 << 5)  # pmod_clk low = ui_in[5]
    await ClockCycles(dut.clk, 2)
    dut.ui_in.value = dut.ui_in.value.integer | (1 << 5)   # pmod_clk high
    await ClockCycles(dut.clk, 3)
    dut.ui_in.value = dut.ui_in.value.integer & ~(1 << 5)  # pmod_clk low
    await ClockCycles(dut.clk, 2)


async def gamepad_pmod_send_buttons(dut, buttons):
    """Send complete button state through PMOD (12 bits)
    
    Args:
        dut: Device under test
        buttons: Dict with button names as keys and 1/0 as values
                 e.g., {'a': 1, 'up': 1} for A and UP pressed
    """
    # Initialize PMOD signals
    ui_val = dut.ui_in.value.integer & 0x0F  # Keep lower 4 bits
    ui_val &= ~(1 << 4)  # pmod_latch low
    ui_val &= ~(1 << 5)  # pmod_clk low
    ui_val &= ~(1 << 6)  # pmod_data low
    dut.ui_in.value = ui_val
    await ClockCycles(dut.clk, 3)
    
    # Send 12 bits (MSB first): B, Y, SELECT, START, UP, DOWN, LEFT, RIGHT, A, X, L, R
    for btn in BUTTON_ORDER:
        bit = 1 if buttons.get(btn, 0) else 0
        await gamepad_pmod_send_bit(dut, bit)
    
    # Latch the data
    await ClockCycles(dut.clk, 3)
    dut.ui_in.value = dut.ui_in.value.integer | (1 << 4)   # pmod_latch high
    await ClockCycles(dut.clk, 5)
    dut.ui_in.value = dut.ui_in.value.integer & ~(1 << 4)  # pmod_latch low
    await ClockCycles(dut.clk, 5)


async def press_button_edge(dut, buttons_before, buttons_after):
    """Simulate button press with edge detection
    
    Many functions are edge-triggered (toggle on 0→1 transition).
    This sends buttons_before state, then buttons_after, then releases.
    """
    await gamepad_pmod_send_buttons(dut, buttons_before)
    await ClockCycles(dut.clk, 5)
    await gamepad_pmod_send_buttons(dut, buttons_after)
    await ClockCycles(dut.clk, 5)
    await gamepad_pmod_send_buttons(dut, {})
    await ClockCycles(dut.clk, 5)


# =============================================================================
# Movement and Painting Functions
# =============================================================================

async def get_signal_safe(dut, *paths):
    """Safely try to get a signal value from multiple possible paths"""
    for path in paths:
        try:
            obj = dut
            for part in path.split('.'):
                obj = getattr(obj, part)
            return int(obj.value)
        except Exception:
            continue
    return None


async def move_and_paint(dut, direction, steps, cycles_per_step=10):
    """Move cursor in a direction while painting
    
    Args:
        dut: Device under test
        direction: 'up', 'down', 'left', 'right'
        steps: Number of steps to move
        cycles_per_step: Clock cycles per step (more = slower, captures more pixels)
    
    Returns:
        Number of pixels read from packet generator
    """
    pixels_read = 0
    
    for step in range(steps):
        # Press direction button
        await gamepad_pmod_send_buttons(dut, {direction: 1})
        
        # Wait and read pixels
        for _ in range(cycles_per_step):
            # Try different signal paths for packet valid
            pkt_valid = await get_signal_safe(dut, 
                'user_project.pkt_inst.valid',
                'pkt_inst.valid',
                'packet_generator_inst.valid')
            
            paint_enable = await get_signal_safe(dut,
                'user_project.colour_inst.paint_enable',
                'colour_inst.paint_enable',
                'paint_enable')
            
            if pkt_valid and paint_enable:
                pkt_x = await get_signal_safe(dut,
                    'user_project.pkt_inst.x_out',
                    'pkt_inst.x_out',
                    'packet_generator_inst.x_out')
                pkt_y = await get_signal_safe(dut,
                    'user_project.pkt_inst.y_out',
                    'pkt_inst.y_out', 
                    'packet_generator_inst.y_out')
                
                # Try to get color from status register or directly
                color = await get_signal_safe(dut,
                    'user_project.status_reg',
                    'status_reg',
                    'user_project.colour_inst.colour_out',
                    'colour_inst.colour_out')
                
                if color is not None:
                    color = color & 0x07
                else:
                    color = 7  # Default to white if can't read
                
                if pkt_x is not None and pkt_y is not None:
                    if 0 <= pkt_x < CANVAS_WIDTH and 0 <= pkt_y < CANVAS_HEIGHT:
                        pygame_state['update_queue'].put({
                            'type': 'pixel', 'x': pkt_x, 'y': pkt_y, 'color': color
                        })
                        pixels_read += 1
            
            # Update cursor position
            x = await get_signal_safe(dut,
                'user_project.pos_inst.x_pos',
                'pos_inst.x_pos',
                'position_inst.x_pos')
            y = await get_signal_safe(dut,
                'user_project.pos_inst.y_pos',
                'pos_inst.y_pos',
                'position_inst.y_pos')
            
            if x is not None and y is not None:
                pygame_state['update_queue'].put({'type': 'cursor', 'x': x, 'y': y})
            
            await ClockCycles(dut.clk, 1)
        
        # Release button
        await gamepad_pmod_send_buttons(dut, {})
        await ClockCycles(dut.clk, 2)
    
    return pixels_read


async def move_quick(dut, direction, steps):
    """Move cursor quickly without painting (for repositioning)"""
    for _ in range(steps):
        await gamepad_pmod_send_buttons(dut, {direction: 1})
        await ClockCycles(dut.clk, 3)
        await gamepad_pmod_send_buttons(dut, {})
        await ClockCycles(dut.clk, 2)
    
    # Update cursor position
    x = await get_signal_safe(dut,
        'user_project.pos_inst.x_pos',
        'pos_inst.x_pos',
        'position_inst.x_pos')
    y = await get_signal_safe(dut,
        'user_project.pos_inst.y_pos',
        'pos_inst.y_pos',
        'position_inst.y_pos')
    
    if x is not None and y is not None:
        pygame_state['update_queue'].put({'type': 'cursor', 'x': x, 'y': y})


async def update_status_from_dut(dut):
    """Read current status from DUT and update pygame display"""
    # Brush size
    brush_size = await get_signal_safe(dut,
        'user_project.brush_inst.brush_size',
        'brush_inst.brush_size',
        'brush_settings_inst.brush_size')
    if brush_size is not None:
        pygame_state['update_queue'].put({'type': 'brush_size', 'size': brush_size + 1})
    
    # Symmetry mode
    sym_mode = await get_signal_safe(dut,
        'user_project.brush_inst.symmetry_mode',
        'brush_inst.symmetry_mode',
        'brush_settings_inst.symmetry_mode')
    if sym_mode is not None:
        sym_names = ['Off', 'H-Mirror', 'V-Mirror', '4-Way']
        pygame_state['update_queue'].put({'type': 'symmetry', 'mode': sym_names[sym_mode & 0x3]})
    
    # Color from status register
    color = await get_signal_safe(dut,
        'user_project.status_reg',
        'status_reg',
        'user_project.colour_inst.colour_out',
        'colour_inst.colour_out')
    if color is not None:
        pygame_state['update_queue'].put({'type': 'color', 'code': color & 0x07})
    
    # Fill mode
    fill_active = await get_signal_safe(dut,
        'user_project.fill_mode_inst.fill_active',
        'fill_mode_inst.fill_active',
        'fill_active')
    if fill_active is not None:
        pygame_state['update_queue'].put({'type': 'fill_mode', 'active': bool(fill_active)})


# =============================================================================
# Main Demo Test
# =============================================================================

@cocotb.test()
async def test_demo_features(dut):
    """Main demo test showcasing all Tiny Canvas features"""
    
    # Start clock FIRST (50MHz = 20ns period)
    cocotb.start_soon(Clock(dut.clk, 20, units="ns").start())
    
    # Reset sequence
    dut.ena.value = 1
    dut.rst_n.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 20)
    
    # Start pygame thread AFTER reset
    pg_thread = threading.Thread(target=pygame_thread, daemon=True)
    pg_thread.start()
    await Timer(50, "ms")  # Brief wait for pygame to initialize
    
    pygame_state['update_queue'].put({'type': 'status', 'text': 'Initializing...'})
    pygame_state['update_queue'].put({'type': 'info', 'text': 'Resetting canvas state'})
    
    # Log available signals for debugging
    dut._log.info("Starting demo initialization...")
    
    # =========================================================================
    # Initialize: Clear all settings to known state
    # =========================================================================
    
    # Ensure freehand mode (not fill mode) - just toggle to be safe
    await press_button_edge(dut, {}, {'select': 1})
    await ClockCycles(dut.clk, 5)
    await press_button_edge(dut, {}, {'select': 1})
    await ClockCycles(dut.clk, 5)
    
    # Reset brush size to minimum (press L a few times)
    for _ in range(4):
        await press_button_edge(dut, {}, {'l': 1})
        await ClockCycles(dut.clk, 2)
    
    # Reset symmetry to Off (cycle through all 4 modes)
    for _ in range(4):
        await press_button_edge(dut, {}, {'start': 1})
        await ClockCycles(dut.clk, 2)
    
    await update_status_from_dut(dut)
    await Timer(50, "ms")
    
    dut._log.info("Initialization complete, starting demos...")
    
    # =========================================================================
    # Demo 1: Brush Sizes
    # =========================================================================
    pygame_state['update_queue'].put({'type': 'status', 'text': 'Demo 1: Brush Sizes'})
    pygame_state['update_queue'].put({'type': 'info', 'text': 'Drawing vertical lines with increasing brush sizes'})
    
    # Enable Red color
    await press_button_edge(dut, {}, {'a': 1})
    await update_status_from_dut(dut)
    await ClockCycles(dut.clk, 10)
    
    # Move to starting position (top-right area)
    await move_quick(dut, 'right', 40)
    await move_quick(dut, 'up', 60)
    
    # Draw 4 vertical lines with increasing brush sizes
    for size_idx in range(4):
        pygame_state['update_queue'].put({'type': 'info', 'text': f'Brush size: {size_idx + 1}x{size_idx + 1}'})
        
        # Increase brush size
        for _ in range(size_idx):
            await press_button_edge(dut, {}, {'r': 1})
            await ClockCycles(dut.clk, 2)
        
        await update_status_from_dut(dut)
        
        # Draw vertical line
        await move_and_paint(dut, 'down', 30, cycles_per_step=15)
        
        # Move right for next line
        await move_quick(dut, 'right', 12)
        await move_quick(dut, 'up', 30)
        
        # Reset brush size for next iteration
        for _ in range(size_idx + 1):
            await press_button_edge(dut, {}, {'l': 1})
            await ClockCycles(dut.clk, 2)
        
        await Timer(100, "ms")
    
    await Timer(150, "ms")
    
    # =========================================================================
    # Demo 2: Color Mixing
    # =========================================================================
    pygame_state['update_queue'].put({'type': 'status', 'text': 'Demo 2: Color Mixing'})
    pygame_state['update_queue'].put({'type': 'info', 'text': 'RGB color combinations'})
    
    # Move to new area
    await move_quick(dut, 'down', 20)
    await move_quick(dut, 'left', 80)
    
    # Colors to demonstrate: R, R+G (Yellow), R+G+B (White), G+B (Cyan), B, G
    color_sequence = [
        ('Red', {'a': 1}, {}),                    # Red only
        ('Yellow (R+G)', {}, {'y': 1}),           # Add Green
        ('White (R+G+B)', {}, {'x': 1}),          # Add Blue
        ('Cyan (G+B)', {'a': 1}, {}),             # Remove Red
        ('Blue', {'y': 1}, {}),                   # Remove Green
        ('Magenta (R+B)', {'a': 1}, {}),          # Add Red
    ]
    
    # Start with Red already on from previous demo
    # Draw colored horizontal lines
    for color_name, toggle_off, toggle_on in color_sequence:
        pygame_state['update_queue'].put({'type': 'info', 'text': f'Color: {color_name}'})
        
        # Toggle colors
        for btn in toggle_off:
            await press_button_edge(dut, {}, {btn: 1})
            await ClockCycles(dut.clk, 3)
        for btn in toggle_on:
            await press_button_edge(dut, {}, {btn: 1})
            await ClockCycles(dut.clk, 3)
        
        await update_status_from_dut(dut)
        
        # Draw horizontal line
        await move_and_paint(dut, 'right', 25, cycles_per_step=10)
        
        # Move down for next line
        await move_quick(dut, 'down', 6)
        await move_quick(dut, 'left', 25)
        
        await Timer(100, "ms")
    
    await Timer(150, "ms")
    
    # =========================================================================
    # Demo 3: Symmetry Modes
    # =========================================================================
    pygame_state['update_queue'].put({'type': 'status', 'text': 'Demo 3: Symmetry Modes'})
    
    # Set color to Magenta (R+B)
    # Current state: R+B from previous demo
    # Clear all, then set R+B
    await press_button_edge(dut, {}, {'y': 1})  # Toggle green off if on
    await update_status_from_dut(dut)
    
    # Set brush size to 2x2
    await press_button_edge(dut, {}, {'r': 1})
    await update_status_from_dut(dut)
    
    # Move to center-ish area
    await move_quick(dut, 'down', 30)
    await move_quick(dut, 'left', 30)
    
    # H-Mirror symmetry
    pygame_state['update_queue'].put({'type': 'info', 'text': 'H-Mirror: Horizontal reflection'})
    await press_button_edge(dut, {}, {'start': 1})  # Cycle to H-Mirror
    await update_status_from_dut(dut)
    await Timer(50, "ms")
    
    await move_and_paint(dut, 'right', 30, cycles_per_step=20)
    await move_quick(dut, 'down', 10)
    await move_quick(dut, 'left', 30)
    await Timer(150, "ms")
    
    # V-Mirror symmetry
    pygame_state['update_queue'].put({'type': 'info', 'text': 'V-Mirror: Vertical reflection'})
    await press_button_edge(dut, {}, {'start': 1})  # Cycle to V-Mirror
    await update_status_from_dut(dut)
    await Timer(50, "ms")
    
    await move_and_paint(dut, 'right', 30, cycles_per_step=20)
    await move_quick(dut, 'down', 10)
    await move_quick(dut, 'left', 30)
    await Timer(150, "ms")
    
    # 4-Way symmetry
    pygame_state['update_queue'].put({'type': 'info', 'text': '4-Way: Both H and V reflection'})
    await press_button_edge(dut, {}, {'start': 1})  # Cycle to 4-Way
    await update_status_from_dut(dut)
    await Timer(50, "ms")
    
    await move_and_paint(dut, 'right', 25, cycles_per_step=25)
    await move_and_paint(dut, 'down', 20, cycles_per_step=25)
    await Timer(150, "ms")
    
    # Reset symmetry to Off
    await press_button_edge(dut, {}, {'start': 1})  # Cycle to Off
    await update_status_from_dut(dut)
    
    await Timer(150, "ms")
    
    # =========================================================================
    # Demo 4: Fill Rectangle
    # =========================================================================
    pygame_state['update_queue'].put({'type': 'status', 'text': 'Demo 4: Fill Rectangle'})
    pygame_state['update_queue'].put({'type': 'info', 'text': 'Drawing filled rectangles'})
    
    # Reset brush size to 1x1
    for _ in range(4):
        await press_button_edge(dut, {}, {'l': 1})
        await ClockCycles(dut.clk, 2)
    
    # Set color to Yellow (R+G) - toggle as needed
    await press_button_edge(dut, {}, {'y': 1})  # Toggle green
    await press_button_edge(dut, {}, {'x': 1})  # Toggle blue off
    await update_status_from_dut(dut)
    
    # Move to corner
    await move_quick(dut, 'left', 50)
    await move_quick(dut, 'down', 40)
    
    # Enable fill mode
    pygame_state['update_queue'].put({'type': 'info', 'text': 'Entering fill mode'})
    await press_button_edge(dut, {}, {'select': 1})
    await ClockCycles(dut.clk, 10)
    await update_status_from_dut(dut)
    await Timer(50, "ms")
    
    # Set corner A
    pygame_state['update_queue'].put({'type': 'info', 'text': 'Setting corner A'})
    await press_button_edge(dut, {}, {'b': 1})
    await ClockCycles(dut.clk, 10)
    await Timer(50, "ms")
    
    # Move to corner B
    await move_quick(dut, 'right', 30)
    await move_quick(dut, 'down', 20)
    
    # Set corner B (triggers fill)
    pygame_state['update_queue'].put({'type': 'info', 'text': 'Setting corner B - Filling...'})
    await press_button_edge(dut, {}, {'b': 1})
    await ClockCycles(dut.clk, 10)
    
    # Read fill pixels
    cycles = 0
    max_cycles = 2000
    pixels_filled = 0
    
    while cycles < max_cycles:
        fill_busy = await get_signal_safe(dut,
            'user_project.fill_draw_inst.busy',
            'fill_draw_inst.busy',
            'fill_busy')
        fill_valid = await get_signal_safe(dut,
            'user_project.fill_draw_inst.pixel_valid',
            'fill_draw_inst.pixel_valid')
        
        if fill_valid:
            fill_x = await get_signal_safe(dut,
                'user_project.fill_draw_inst.x_out',
                'fill_draw_inst.x_out')
            fill_y = await get_signal_safe(dut,
                'user_project.fill_draw_inst.y_out',
                'fill_draw_inst.y_out')
            color = await get_signal_safe(dut,
                'user_project.status_reg',
                'status_reg')
            
            if fill_x is not None and fill_y is not None:
                color_val = (color & 0x07) if color is not None else 6
                if 0 <= fill_x < CANVAS_WIDTH and 0 <= fill_y < CANVAS_HEIGHT:
                    pygame_state['update_queue'].put({
                        'type': 'pixel', 'x': fill_x, 'y': fill_y, 'color': color_val
                    })
                    pixels_filled += 1
        
        # Exit if not busy anymore
        if fill_busy is not None and not fill_busy and cycles > 100:
            break
        
        await ClockCycles(dut.clk, 1)
        cycles += 1
    
    pygame_state['update_queue'].put({'type': 'info', 'text': f'Filled {pixels_filled} pixels'})
    
    # Exit fill mode
    await press_button_edge(dut, {}, {'select': 1})
    await update_status_from_dut(dut)
    
    await Timer(250, "ms")
    
    # =========================================================================
    # Demo 5: Undo/Redo
    # =========================================================================
    pygame_state['update_queue'].put({'type': 'status', 'text': 'Demo 5: Undo/Redo'})
    pygame_state['update_queue'].put({'type': 'info', 'text': 'Drawing line then undoing'})
    
    # Set color to Cyan (G+B) - toggle as needed
    await press_button_edge(dut, {}, {'a': 1})  # Toggle red
    await press_button_edge(dut, {}, {'x': 1})  # Toggle blue
    await update_status_from_dut(dut)
    
    # Move to new area
    await move_quick(dut, 'up', 30)
    await move_quick(dut, 'right', 40)
    
    # Draw something that will be undone
    await move_and_paint(dut, 'down', 25, cycles_per_step=15)
    await move_and_paint(dut, 'left', 15, cycles_per_step=15)
    
    await Timer(200, "ms")
    
    # Undo (L+R combination)
    pygame_state['update_queue'].put({'type': 'info', 'text': 'Performing Undo (L+R)'})
    await gamepad_pmod_send_buttons(dut, {'l': 1, 'r': 1})
    await ClockCycles(dut.clk, 15)
    await gamepad_pmod_send_buttons(dut, {})
    await ClockCycles(dut.clk, 15)
    
    # Read undo restore pixels
    undo_pixels = 0
    for _ in range(80):
        undo_valid = await get_signal_safe(dut,
            'user_project.undo_inst.restore_valid',
            'undo_inst.restore_valid',
            'undo_redo_inst.restore_valid')
        
        if undo_valid:
            ux = await get_signal_safe(dut,
                'user_project.undo_inst.x_out',
                'undo_inst.x_out',
                'undo_redo_inst.x_out')
            uy = await get_signal_safe(dut,
                'user_project.undo_inst.y_out',
                'undo_inst.y_out',
                'undo_redo_inst.y_out')
            uc = await get_signal_safe(dut,
                'user_project.undo_inst.color_out',
                'undo_inst.color_out',
                'undo_redo_inst.color_out')
            
            if ux is not None and uy is not None:
                color_val = uc if uc is not None else 0
                if 0 <= ux < CANVAS_WIDTH and 0 <= uy < CANVAS_HEIGHT:
                    pygame_state['update_queue'].put({
                        'type': 'pixel', 'x': ux, 'y': uy, 'color': color_val
                    })
                    undo_pixels += 1
        await ClockCycles(dut.clk, 2)
    
    pygame_state['update_queue'].put({'type': 'info', 'text': f'Undo restored {undo_pixels} pixels'})
    await Timer(250, "ms")
    
    # Redo (Select+Start combination)
    pygame_state['update_queue'].put({'type': 'info', 'text': 'Performing Redo (Select+Start)'})
    await gamepad_pmod_send_buttons(dut, {'select': 1, 'start': 1})
    await ClockCycles(dut.clk, 15)
    await gamepad_pmod_send_buttons(dut, {})
    await ClockCycles(dut.clk, 15)
    
    # Read redo restore pixels
    redo_pixels = 0
    for _ in range(80):
        redo_valid = await get_signal_safe(dut,
            'user_project.undo_inst.restore_valid',
            'undo_inst.restore_valid',
            'undo_redo_inst.restore_valid')
        
        if redo_valid:
            rx = await get_signal_safe(dut,
                'user_project.undo_inst.x_out',
                'undo_inst.x_out',
                'undo_redo_inst.x_out')
            ry = await get_signal_safe(dut,
                'user_project.undo_inst.y_out',
                'undo_inst.y_out',
                'undo_redo_inst.y_out')
            rc = await get_signal_safe(dut,
                'user_project.undo_inst.color_out',
                'undo_inst.color_out',
                'undo_redo_inst.color_out')
            
            if rx is not None and ry is not None:
                color_val = rc if rc is not None else 0
                if 0 <= rx < CANVAS_WIDTH and 0 <= ry < CANVAS_HEIGHT:
                    pygame_state['update_queue'].put({
                        'type': 'pixel', 'x': rx, 'y': ry, 'color': color_val
                    })
                    redo_pixels += 1
        await ClockCycles(dut.clk, 2)
    
    pygame_state['update_queue'].put({'type': 'info', 'text': f'Redo restored {redo_pixels} pixels'})
    await Timer(250, "ms")
    
    # =========================================================================
    # Demo Complete
    # =========================================================================
    pygame_state['update_queue'].put({'type': 'status', 'text': 'Demo Complete! ✅'})
    pygame_state['update_queue'].put({'type': 'info', 'text': 'All features demonstrated successfully'})
    
    dut._log.info("Demo completed successfully!")
    
    # Keep display open for a couple seconds
    await Timer(2, "sec")
    
    # Signal pygame to close
    pygame_state['running'] = False
    
    # Wait for pygame thread to finish
    pg_thread.join(timeout=1.0)
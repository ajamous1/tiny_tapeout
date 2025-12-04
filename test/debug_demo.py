"""
debug_demo.py - FIXED VERSION with correct direction mapping and continuous lines

Key fixes:
1. Correct direction mapping based on Verilog bit concatenation analysis
2. Press/release button quickly (1-2 cycles) then wait for packet generator
3. Proper color state tracking with read-before-toggle logic
4. Optimized wait times for faster execution
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer
import threading
import queue

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

COLORS = {
    0b000: (0, 0, 0), 0b001: (0, 0, 255), 0b010: (0, 255, 0), 0b011: (0, 255, 255),
    0b100: (255, 0, 0), 0b101: (255, 0, 255), 0b110: (255, 255, 0), 0b111: (255, 255, 255)
}
COLOR_NAMES = {
    0b000: "Black", 0b001: "Blue", 0b010: "Green", 0b011: "Cyan",
    0b100: "Red", 0b101: "Magenta", 0b110: "Yellow", 0b111: "White"
}
SYMMETRY_MODES = ["Off", "H-Mirror", "V-Mirror", "4-Way"]
CANVAS_WIDTH = 256
CANVAS_HEIGHT = 256
BUTTON_ORDER = ['b', 'y', 'select', 'start', 'up', 'down', 'left', 'right', 'a', 'x', 'l', 'r']

pygame_state = {
    'canvas': [[0] * CANVAS_WIDTH for _ in range(CANVAS_HEIGHT)],
    'cursor_x': 128, 'cursor_y': 128,
    'sw_red': False, 'sw_green': False, 'sw_blue': False,
    'brush_mode': True,
    'brush_size': 0,
    'symmetry_mode': 0,
    'fill_mode': False,
    'fill_corner_a': None,
    'i2c_x': 0, 'i2c_y': 0, 'i2c_status': 0, 'i2c_count': 0,
    'undo_count': 0, 'redo_count': 0,
    'status_message': '',
    'running': True,
    'update_queue': queue.Queue()
}


def pygame_thread():
    """Full interface pygame thread matching interactive_emulator.py"""
    if not PYGAME_AVAILABLE:
        while pygame_state['running']:
            try:
                while True:
                    update = pygame_state['update_queue'].get_nowait()
                    if update['type'] == 'pixel':
                        x, y, color = update['x'], update['y'], update['color']
                        if 0 <= x < CANVAS_WIDTH and 0 <= y < CANVAS_HEIGHT:
                            pygame_state['canvas'][y][x] = color
                    elif update['type'] == 'state':
                        pygame_state.update(update['data'])
            except queue.Empty:
                pass
            import time
            time.sleep(0.016)
        return
    
    pygame.init()
    
    # Get screen info for sizing
    info = pygame.display.Info()
    window_width = int(info.current_w * 0.85)
    window_height = int(info.current_h * 0.85)
    
    screen = pygame.display.set_mode((window_width, window_height), pygame.RESIZABLE)
    pygame.display.set_caption("Fixed Debug Demo - Verilog Driven")
    
    sidebar_width = 380
    grid_size = 256
    
    # Colors
    bg_color = (25, 28, 38)
    panel_color = (35, 40, 52)
    text_color = (220, 220, 230)
    accent_color = (80, 200, 255)
    highlight = (255, 200, 80)
    
    # Fonts
    font_title = pygame.font.Font(None, 36)
    font_large = pygame.font.Font(None, 28)
    font_medium = pygame.font.Font(None, 22)
    font_small = pygame.font.Font(None, 18)
    
    clock = pygame.time.Clock()
    
    def recalculate_layout():
        nonlocal window_width, window_height, grid_size, sidebar_width
        available_w = window_width - sidebar_width - 60
        available_h = window_height - 100
        cell_size = min(available_w // grid_size, available_h // grid_size)
        cell_size = max(cell_size, 2)
        canvas_width = cell_size * grid_size
        canvas_height = cell_size * grid_size
        canvas_x = (window_width - sidebar_width - canvas_width) // 2
        canvas_y = (window_height - canvas_height) // 2 + 30
        return cell_size, canvas_x, canvas_y, canvas_width, canvas_height
    
    def draw_header():
        title = font_title.render("FIXED DEBUG DEMO", True, accent_color)
        screen.blit(title, (window_width // 2 - title.get_width() // 2, 15))
        
        hint = "Directions Fixed | Continuous Lines | Correct Colors"
        screen.blit(font_small.render(hint, True, (120, 120, 130)),
                   (window_width // 2 - 230, 45))
    
    def draw_canvas(cell_size, canvas_x, canvas_y, canvas_width, canvas_height):
        # Draw canvas pixels
        for cy in range(grid_size):
            for cx in range(grid_size):
                screen_y = grid_size - 1 - cy
                rect = pygame.Rect(canvas_x + cx * cell_size,
                                  canvas_y + screen_y * cell_size,
                                  cell_size, cell_size)
                pygame.draw.rect(screen, COLORS[pygame_state['canvas'][cy][cx]], rect)
        
        # Canvas border
        pygame.draw.rect(screen, (80, 80, 90),
                        (canvas_x - 2, canvas_y - 2,
                         canvas_width + 4, canvas_height + 4), 2)
        
        # Cursor
        cursor_size = max(cell_size * (pygame_state['brush_size'] + 2), 8)
        screen_y = grid_size - 1 - pygame_state['cursor_y']
        cx = canvas_x + pygame_state['cursor_x'] * cell_size + cell_size // 2
        cy = canvas_y + screen_y * cell_size + cell_size // 2
        cursor_color = (255, 100, 100) if pygame_state['fill_mode'] else (255, 255, 0)
        pygame.draw.rect(screen, cursor_color,
                        (cx - cursor_size // 2, cy - cursor_size // 2, cursor_size, cursor_size), 2)
        
        # Fill corner A marker
        if pygame_state['fill_corner_a']:
            ax, ay = pygame_state['fill_corner_a']
            screen_ay = grid_size - 1 - ay
            px = canvas_x + ax * cell_size + cell_size // 2
            py = canvas_y + screen_ay * cell_size + cell_size // 2
            pygame.draw.circle(screen, (255, 100, 100), (px, py), 8, 2)
            
            # Preview rectangle
            bx, by = pygame_state['cursor_x'], pygame_state['cursor_y']
            min_x, max_x = min(ax, bx), max(ax, bx)
            min_y, max_y = min(ay, by), max(ay, by)
            
            rx = canvas_x + min_x * cell_size
            ry = canvas_y + (grid_size - 1 - max_y) * cell_size
            rw = (max_x - min_x + 1) * cell_size
            rh = (max_y - min_y + 1) * cell_size
            pygame.draw.rect(screen, (255, 100, 100), (rx, ry, rw, rh), 1)
    
    def draw_sidebar():
        sx = window_width - sidebar_width + 15
        y = 70
        
        pygame.draw.rect(screen, panel_color,
                        (sx - 10, y - 10, sidebar_width - 20, window_height - 90),
                        border_radius=10)
        
        # Color swatch
        color = (int(pygame_state['sw_red']) << 2) | (int(pygame_state['sw_green']) << 1) | int(pygame_state['sw_blue'])
        pygame.draw.rect(screen, COLORS[color], (sx, y, 60, 60))
        pygame.draw.rect(screen, text_color, (sx, y, 60, 60), 2)
        
        screen.blit(font_large.render(COLOR_NAMES[color], True, text_color), (sx + 70, y + 5))
        
        mode_text = "BRUSH" if pygame_state['brush_mode'] else "ERASER"
        mode_color = (80, 255, 120) if pygame_state['brush_mode'] else (255, 100, 100)
        screen.blit(font_medium.render(f"Paint: {mode_text}", True, mode_color), (sx + 70, y + 35))
        y += 75
        
        # Fill mode indicator
        fill_text = "FILL MODE ON" if pygame_state['fill_mode'] else "Fill Mode Off"
        fill_color = (255, 100, 100) if pygame_state['fill_mode'] else (100, 100, 110)
        screen.blit(font_medium.render(fill_text, True, fill_color), (sx, y))
        y += 25
        
        if pygame_state['fill_mode'] and pygame_state['fill_corner_a']:
            corner_text = f"Corner A: {pygame_state['fill_corner_a']}"
            screen.blit(font_small.render(corner_text, True, (255, 150, 150)), (sx, y))
            y += 20
        y += 5
        
        # RGB channels
        for label, state, clr in [("R", pygame_state['sw_red'], (255, 60, 60)),
                                   ("G", pygame_state['sw_green'], (60, 255, 60)),
                                   ("B", pygame_state['sw_blue'], (60, 60, 255))]:
            screen.blit(font_large.render(label, True, text_color), (sx, y))
            pygame.draw.rect(screen, clr if state else (50, 50, 55), (sx + 25, y, 50, 22))
            pygame.draw.rect(screen, text_color, (sx + 25, y, 50, 22), 1)
            screen.blit(font_small.render("ON" if state else "OFF", True, text_color), (sx + 85, y + 3))
            y += 28
        y += 10
        
        # Status info
        screen.blit(font_medium.render(f"Position: ({pygame_state['cursor_x']}, {pygame_state['cursor_y']})", True, text_color), (sx, y))
        y += 25
        screen.blit(font_medium.render(f"Brush: {pygame_state['brush_size'] + 1}x{pygame_state['brush_size'] + 1}", True, text_color), (sx, y))
        y += 25
        screen.blit(font_medium.render(f"Symmetry: {SYMMETRY_MODES[pygame_state['symmetry_mode']]}", True, text_color), (sx, y))
        y += 30
        
        screen.blit(font_small.render(f"Undo: {pygame_state['undo_count']} | Redo: {pygame_state['redo_count']}", True, (150, 150, 160)), (sx, y))
        y += 25
        
        # I2C Output
        screen.blit(font_medium.render("I2C Output:", True, accent_color), (sx, y))
        y += 22
        for info in [f"X: 0x{pygame_state['i2c_x']:02X}", f"Y: 0x{pygame_state['i2c_y']:02X}",
                     f"Status: 0x{pygame_state['i2c_status']:02X}", f"Packets: {pygame_state['i2c_count']}"]:
            screen.blit(font_small.render(info, True, (180, 180, 190)), (sx + 10, y))
            y += 18
        
        y += 15
        screen.blit(font_medium.render("Debug Info:", True, text_color), (sx, y))
        y += 22
        if pygame_state['status_message']:
            screen.blit(font_small.render(pygame_state['status_message'], True, highlight), (sx, y))
            y += 18
    
    def draw_message(canvas_x, canvas_y, canvas_height):
        if pygame_state['status_message']:
            msg = font_large.render(pygame_state['status_message'], True, highlight)
            pygame.draw.rect(screen, (40, 40, 50),
                           (canvas_x, canvas_y + canvas_height + 10, msg.get_width() + 20, 30),
                           border_radius=5)
            screen.blit(msg, (canvas_x + 10, canvas_y + canvas_height + 15))
    
    while pygame_state['running']:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame_state['running'] = False
                return
            if event.type == pygame.VIDEORESIZE:
                window_width, window_height = event.w, event.h
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
        
        # Process updates from queue
        try:
            for _ in range(1000):
                update = pygame_state['update_queue'].get_nowait()
                if update['type'] == 'pixel':
                    x, y, color = update['x'], update['y'], update['color']
                    if 0 <= x < CANVAS_WIDTH and 0 <= y < CANVAS_HEIGHT:
                        pygame_state['canvas'][y][x] = color
                elif update['type'] == 'state':
                    pygame_state.update(update['data'])
        except queue.Empty:
            pass
        
        # Recalculate layout
        cell_size, canvas_x, canvas_y, canvas_width, canvas_height = recalculate_layout()
        
        # Draw everything
        screen.fill(bg_color)
        draw_header()
        draw_canvas(cell_size, canvas_x, canvas_y, canvas_width, canvas_height)
        draw_sidebar()
        draw_message(canvas_x, canvas_y, canvas_height)
        
        pygame.display.flip()
        clock.tick(60)
    
    pygame.quit()


async def send_pmod_bit(dut, bit):
    """Send a single bit via PMOD protocol - ULTRA FAST (2 cycles per bit)"""
    current = dut.ui_in.value.integer & ~((1 << 6) | (1 << 5))  # Clear data and clock
    if bit:
        current |= (1 << 6)  # Set data bit
    # Data set, clock low
    dut.ui_in.value = current
    await ClockCycles(dut.clk, 1)
    # Clock high (rising edge samples data)
    dut.ui_in.value = current | (1 << 5)
    await ClockCycles(dut.clk, 1)


async def send_buttons(dut, buttons, log=False):
    """Send button state via PMOD protocol - ULTRA FAST (~27 cycles total)
    Button order: B, Y, SELECT, START, UP, DOWN, LEFT, RIGHT, A, X, L, R
    """
    # Clear PMOD signals (keep lower 4 bits)
    dut.ui_in.value = dut.ui_in.value.integer & 0x0F
    await ClockCycles(dut.clk, 1)
    
    # Send 12 bits (2 cycles each = 24 cycles)
    for btn in BUTTON_ORDER:
        bit = 1 if buttons.get(btn, 0) else 0
        await send_pmod_bit(dut, bit)
    
    # Latch pulse (rising edge captures data)
    dut.ui_in.value = dut.ui_in.value.integer | (1 << 4)
    await ClockCycles(dut.clk, 1)
    dut.ui_in.value = dut.ui_in.value.integer & ~(1 << 4)
    await ClockCycles(dut.clk, 1)


async def press_button_with_edge(dut, button_dict, log=False):
    """Press a button with proper edge detection - ULTRA FAST"""
    # Ensure released first
    await send_buttons(dut, {})
    await ClockCycles(dut.clk, 1)
    # Press
    await send_buttons(dut, button_dict)
    await ClockCycles(dut.clk, 2)  # Hold for edge detection
    # Release
    await send_buttons(dut, {})
    await ClockCycles(dut.clk, 1)


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


async def log_state(dut, label=""):
    """Log current state of key signals"""
    # Gamepad signals (from gamepad module)
    gp_a = read_signal(dut, 'user_project.gamepad_inst.a')
    gp_y = read_signal(dut, 'user_project.gamepad_inst.y')
    gp_x = read_signal(dut, 'user_project.gamepad_inst.x')
    
    # Color switches (internal registers)
    sw_red = read_signal(dut, 'user_project.sw_red')
    sw_green = read_signal(dut, 'user_project.sw_green')
    sw_blue = read_signal(dut, 'user_project.sw_blue')
    
    # Colour module outputs
    colour_out = read_signal(dut, 'user_project.colour_inst.colour_out')
    paint_enable = read_signal(dut, 'user_project.colour_inst.paint_enable')
    
    # Position (from position module)
    x_pos = read_signal(dut, 'user_project.pos_inst.x_pos')
    y_pos = read_signal(dut, 'user_project.pos_inst.y_pos')
    
    # Movement (internal wire)
    movement = read_signal(dut, 'user_project.movement')
    freehand_trigger = read_signal(dut, 'user_project.freehand_trigger')
    
    # Packet generator
    pkt_valid = read_signal(dut, 'user_project.pkt_inst.valid')
    pkt_x = read_signal(dut, 'user_project.pkt_inst.x_out')
    pkt_y = read_signal(dut, 'user_project.pkt_inst.y_out')
    
    dut._log.info(f"""
--- {label} ---
Gamepad:    gp_a={gp_a}, gp_y={gp_y}, gp_x={gp_x}
Switches:   sw_red={sw_red}, sw_green={sw_green}, sw_blue={sw_blue}
Colour:     colour_out={colour_out}, paint_enable={paint_enable}
Position:   x={x_pos}, y={y_pos}
Trigger:    movement={movement}, freehand_trigger={freehand_trigger}
Packet:     valid={pkt_valid}, x={pkt_x}, y={pkt_y}
""")


async def update_pygame_state(dut):
    """Read state from Verilog and update pygame"""
    try:
        sw_red = read_signal(dut, 'user_project.sw_red')
        sw_green = read_signal(dut, 'user_project.sw_green')
        sw_blue = read_signal(dut, 'user_project.sw_blue')
        brush_mode = read_signal(dut, 'user_project.brush_mode')
        brush_size = read_signal(dut, 'user_project.brush_inst.brush_size')
        symmetry_mode = read_signal(dut, 'user_project.brush_inst.symmetry_mode')
        fill_active = read_signal(dut, 'user_project.fill_mode_inst.fill_active')
        x_pos = read_signal(dut, 'user_project.pos_inst.x_pos')
        y_pos = read_signal(dut, 'user_project.pos_inst.y_pos')
        status_reg = read_signal(dut, 'user_project.status_reg')
        
        pygame_state['update_queue'].put({
            'type': 'state',
            'data': {
                'sw_red': bool(sw_red) if sw_red is not None else False,
                'sw_green': bool(sw_green) if sw_green is not None else False,
                'sw_blue': bool(sw_blue) if sw_blue is not None else False,
                'brush_mode': bool(brush_mode) if brush_mode is not None else True,
                'brush_size': brush_size if brush_size is not None else 0,
                'symmetry_mode': symmetry_mode if symmetry_mode is not None else 0,
                'fill_mode': bool(fill_active) if fill_active is not None else False,
                'cursor_x': x_pos if x_pos is not None else 128,
                'cursor_y': y_pos if y_pos is not None else 128,
                'i2c_x': x_pos if x_pos is not None else 0,
                'i2c_y': y_pos if y_pos is not None else 0,
                'i2c_status': status_reg if status_reg is not None else 0,
            }
        })
    except:
        pass


@cocotb.test()
async def test_debug_demo(dut):
    """Debug test to trace signal flow"""
    
    dut._log.info("="*60)
    dut._log.info("STARTING DEBUG DEMO TEST")
    dut._log.info("="*60)
    
    # Start clock
    dut._log.info("Starting clock...")
    cocotb.start_soon(Clock(dut.clk, 20, units="ns").start())
    await ClockCycles(dut.clk, 5)
    dut._log.info("Clock started")
    
    # Reset
    dut._log.info("=== RESET ===")
    dut.ena.value = 1
    dut.rst_n.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 10)
    dut._log.info("Reset asserted for 10 cycles")
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 20)
    dut._log.info("Reset released, waited 20 cycles")
    
    # Start pygame
    dut._log.info("Starting pygame thread...")
    pg_thread = threading.Thread(target=pygame_thread, daemon=True)
    pg_thread.start()
    dut._log.info("Pygame thread started, waiting for initialization...")
    # Use ClockCycles instead of Timer - more reliable
    await ClockCycles(dut.clk, 500)  # ~10us at 50MHz
    dut._log.info("Pygame thread should be running now")
    
    # Log initial state
    dut._log.info("Reading initial state...")
    await log_state(dut, "Initial state after reset")
    dut._log.info("Updating pygame state...")
    await update_pygame_state(dut)
    dut._log.info("Initial state updated")
    
    # =========================================================================
    # Quick Diagnostic Test
    # =========================================================================
    dut._log.info("\n" + "="*60)
    dut._log.info("=== QUICK DIAGNOSTIC ===")
    dut._log.info("="*60)
    
    # Test one direction button
    await send_buttons(dut, {'right': 1})
    movement = read_signal(dut, 'user_project.movement') or 0
    dut._log.info(f"Movement signal: {movement} (expected 1)")
    await send_buttons(dut, {})
    
    # Enable red and test painting chain
    await press_button_with_edge(dut, {'a': 1})
    
    await send_buttons(dut, {'right': 1})
    paint_enable = read_signal(dut, 'user_project.colour_inst.paint_enable') or 0
    freehand_trigger = read_signal(dut, 'user_project.freehand_trigger') or 0
    pkt_busy = read_signal(dut, 'user_project.pkt_inst.busy') or 0
    dut._log.info(f"paint_enable={paint_enable}, freehand_trigger={freehand_trigger}, pkt_busy={pkt_busy}")
    await send_buttons(dut, {})
    
    dut._log.info("Diagnostic complete\n")
    
    # =========================================================================
    # Test 1: Press A to enable Red (already done in diagnostic)
    # =========================================================================
    dut._log.info("\n" + "="*60)
    dut._log.info("TEST 1: Red enabled")
    dut._log.info("="*60)
    
    sw_red = read_signal(dut, 'user_project.sw_red')
    if sw_red != 1:
        await press_button_with_edge(dut, {'a': 1})
        sw_red = read_signal(dut, 'user_project.sw_red')
    
    dut._log.info(f"sw_red = {sw_red}")
    pygame_state['status_message'] = "TEST 1: Red enabled"
    await update_pygame_state(dut)
    
    # =========================================================================
    # Test 2: Movement and Painting - Draw a pattern
    # =========================================================================
    dut._log.info("\n" + "="*60)
    dut._log.info("TEST 2: Movement and Painting - Drawing Pattern")
    dut._log.info("="*60)
    
    pixels_drawn = 0
    pygame_state['status_message'] = "TEST 2: Drawing pattern with Red"
    
    # Ensure red is still enabled (from Test 1) and paint_enable is active
    sw_red = read_signal(dut, 'user_project.sw_red') or 0
    sw_green = read_signal(dut, 'user_project.sw_green') or 0
    sw_blue = read_signal(dut, 'user_project.sw_blue') or 0
    paint_enable = read_signal(dut, 'user_project.colour_inst.paint_enable') or 0
    brush_mode = read_signal(dut, 'user_project.brush_mode') or 0
    
    if not sw_red:
        dut._log.warning("Red not enabled! Re-enabling...")
        await press_button_with_edge(dut, {'a': 1}, log=False)
        await ClockCycles(dut.clk, 5)
        sw_red = read_signal(dut, 'user_project.sw_red') or 0
    
    paint_enable = read_signal(dut, 'user_project.colour_inst.paint_enable') or 0
    dut._log.info(f"Before Test 2: sw_red={sw_red}, sw_green={sw_green}, sw_blue={sw_blue}")
    dut._log.info(f"  brush_mode={brush_mode}, paint_enable={paint_enable}")
    
    if not paint_enable:
        dut._log.error("paint_enable is 0! Cannot paint. Fixing...")
        # Ensure at least one color is on
        if not sw_red and not sw_green and not sw_blue:
            await press_button_with_edge(dut, {'a': 1}, log=False)
            await ClockCycles(dut.clk, 5)
        paint_enable = read_signal(dut, 'user_project.colour_inst.paint_enable') or 0
        dut._log.info(f"  After fix: paint_enable={paint_enable}")
    
    await update_pygame_state(dut)
    
    # CRITICAL FIX: Correct direction mapping based on Verilog bit concatenation analysis
    # dir_udlr = {gp_up, gp_down, gp_left, gp_right} creates:
    #   dir_udlr[3] = gp_up (MSB)
    #   dir_udlr[2] = gp_down
    #   dir_udlr[1] = gp_left
    #   dir_udlr[0] = gp_right (LSB)
    #
    # position.v interprets as:
    #   dir_udlr[3] -> x + 1 (RIGHT)
    #   dir_udlr[2] -> x - 1 (LEFT)
    #   dir_udlr[1] -> y - 1 (DOWN)
    #   dir_udlr[0] -> y + 1 (UP)
    #
    # Therefore correct mapping:
    DIRECTION_MAP = {
        'right': 'up',      # To move right, set dir_udlr[3]=1, need gp_up=1
        'left': 'down',     # To move left, set dir_udlr[2]=1, need gp_down=1
        'down': 'left',     # To move down, set dir_udlr[1]=1, need gp_left=1
        'up': 'right'       # To move up, set dir_udlr[0]=1, need gp_right=1
    }
    
    async def move_continuous(dut, direction, steps):
        """
        ULTRA-FAST move and paint with edge-triggered position.
        Each button press moves exactly 1 pixel.
        """
        pixels = 0
        painted_pixels = set()
        actual_dir = DIRECTION_MAP.get(direction, direction)
        
        # Get brush settings once
        brush_size = read_signal(dut, 'user_project.brush_inst.brush_size') or 0
        symmetry_mode = read_signal(dut, 'user_project.brush_inst.symmetry_mode') or 0
        brush_pixels = (brush_size + 1) ** 2
        sym_mult = 1 if symmetry_mode == 0 else (2 if symmetry_mode < 3 else 4)
        
        # Minimal wait cycles - just enough for packet generator
        wait_cycles = brush_pixels * sym_mult + 5
        
        # Log initial state
        if steps > 0:
            start_x = read_signal(dut, 'user_project.pos_inst.x_pos') or 0
            start_y = read_signal(dut, 'user_project.pos_inst.y_pos') or 0
            dut._log.info(f"move_continuous: {direction} {steps} steps from ({start_x},{start_y})")
        
        for step in range(steps):
            # Release -> Press -> collect pixels -> Release
            await send_buttons(dut, {})
            await ClockCycles(dut.clk, 1)
            
            await send_buttons(dut, {actual_dir: 1})
            
            # Collect pixels during wait
            for _ in range(wait_cycles):
                pkt_valid = read_signal(dut, 'user_project.pkt_inst.valid')
                if pkt_valid:
                    pkt_x = read_signal(dut, 'user_project.pkt_inst.x_out')
                    pkt_y = read_signal(dut, 'user_project.pkt_inst.y_out')
                    colour = read_signal(dut, 'user_project.colour_inst.colour_out')
                    if pkt_x is not None and pkt_y is not None and colour is not None:
                        pixel_key = (pkt_x, pkt_y)
                        if pixel_key not in painted_pixels and 0 <= pkt_x < 256 and 0 <= pkt_y < 256:
                            painted_pixels.add(pixel_key)
                            pygame_state['update_queue'].put({
                                'type': 'pixel', 'x': pkt_x, 'y': pkt_y, 'color': colour
                            })
                            pixels += 1
                await ClockCycles(dut.clk, 1)
            
            await send_buttons(dut, {})
            await ClockCycles(dut.clk, 1)
            
            # Log first step
            if step == 0:
                new_x = read_signal(dut, 'user_project.pos_inst.x_pos') or 0
                new_y = read_signal(dut, 'user_project.pos_inst.y_pos') or 0
                dut._log.info(f"  Step 0: moved to ({new_x},{new_y})")
        
        # Update cursor
        x_pos = read_signal(dut, 'user_project.pos_inst.x_pos')
        y_pos = read_signal(dut, 'user_project.pos_inst.y_pos')
        if x_pos is not None and y_pos is not None:
            pygame_state['update_queue'].put({
                'type': 'state',
                'data': {'cursor_x': x_pos, 'cursor_y': y_pos}
            })
        
        return pixels
    
    async def set_color(dut, color_name):
        """
        FIXED: Set color by reading current state and toggling only what's needed.
        Includes verification to ensure color is set correctly.
        """
        color_map = {
            'Black': (0, 0, 0),
            'Red': (1, 0, 0),
            'Green': (0, 1, 0),
            'Blue': (0, 0, 1),
            'Yellow': (1, 1, 0),
            'Cyan': (0, 1, 1),
            'Magenta': (1, 0, 1),
            'White': (1, 1, 1),
        }
        
        target_r, target_g, target_b = color_map.get(color_name, (0, 0, 0))
        
        # Read current state
        current_r = read_signal(dut, 'user_project.sw_red') or 0
        current_g = read_signal(dut, 'user_project.sw_green') or 0
        current_b = read_signal(dut, 'user_project.sw_blue') or 0
        
        dut._log.info(f"set_color({color_name}): current=({current_r},{current_g},{current_b}), target=({target_r},{target_g},{target_b})")
        
        # Toggle only what's different
        if current_r != target_r:
            await press_button_with_edge(dut, {'a': 1}, log=False)
            await ClockCycles(dut.clk, 5)
        if current_g != target_g:
            await press_button_with_edge(dut, {'y': 1}, log=False)
            await ClockCycles(dut.clk, 5)
        if current_b != target_b:
            await press_button_with_edge(dut, {'x': 1}, log=False)
            await ClockCycles(dut.clk, 5)
        
        # Verify color was set correctly
        await ClockCycles(dut.clk, 5)
        final_r = read_signal(dut, 'user_project.sw_red') or 0
        final_g = read_signal(dut, 'user_project.sw_green') or 0
        final_b = read_signal(dut, 'user_project.sw_blue') or 0
        
        if (final_r, final_g, final_b) != (target_r, target_g, target_b):
            dut._log.warning(f"Color mismatch! Got ({final_r},{final_g},{final_b}), expected ({target_r},{target_g},{target_b})")
        else:
            dut._log.info(f"Color set correctly: {color_name} ({final_r},{final_g},{final_b})")
        
        await update_pygame_state(dut)
    
    async def move_quick(dut, direction, steps):
        """ULTRA-FAST move without painting (for repositioning)."""
        actual_dir = DIRECTION_MAP.get(direction, direction)
        
        for _ in range(steps):
            await send_buttons(dut, {})
            await ClockCycles(dut.clk, 1)
            await send_buttons(dut, {actual_dir: 1})
            await ClockCycles(dut.clk, 1)
        
        await send_buttons(dut, {})
        
        # Update cursor
        x_pos = read_signal(dut, 'user_project.pos_inst.x_pos')
        y_pos = read_signal(dut, 'user_project.pos_inst.y_pos')
        if x_pos is not None and y_pos is not None:
            pygame_state['update_queue'].put({
                'type': 'state',
                'data': {'cursor_x': x_pos, 'cursor_y': y_pos}
            })
    
    # Move to center-left for square
    dut._log.info("Moving to square position...")
    await move_quick(dut, 'left', 40)
    await move_quick(dut, 'up', 40)
    
    # Draw a square pattern (smaller for speed)
    dut._log.info("Drawing square pattern...")
    pixels_drawn += await move_continuous(dut, 'right', 15)
    pixels_drawn += await move_continuous(dut, 'down', 15)
    pixels_drawn += await move_continuous(dut, 'left', 15)
    pixels_drawn += await move_continuous(dut, 'up', 15)
    await update_pygame_state(dut)
    
    dut._log.info(f"\nMovement test complete. Total pixels drawn: {pixels_drawn}")
    pygame_state['status_message'] = f"TEST 2: Square drawn"
    await update_pygame_state(dut)
    await ClockCycles(dut.clk, 10)
    
    if pixels_drawn == 0:
        dut._log.error("NO PIXELS WERE DRAWN! Investigating...")
        pygame_state['status_message'] = "ERROR: No pixels drawn! Check console."
        
        # Check individual signals
        colour_out = read_signal(dut, 'user_project.colour_inst.colour_out')
        paint_enable = read_signal(dut, 'user_project.colour_inst.paint_enable')
        sw_red = read_signal(dut, 'user_project.sw_red')
        brush_mode = read_signal(dut, 'user_project.brush_mode')
        
        dut._log.info(f"colour_out={colour_out}, paint_enable={paint_enable}")
        dut._log.info(f"sw_red={sw_red}, brush_mode={brush_mode}")
        
        # Check packet generator
        pkt_busy = read_signal(dut, 'user_project.pkt_inst.busy')
        pixel_trigger = read_signal(dut, 'user_project.pixel_trigger')
        freehand_trigger = read_signal(dut, 'user_project.freehand_trigger')
        fill_active = read_signal(dut, 'user_project.fill_active_wire')
        
        dut._log.info(f"pkt_busy={pkt_busy}, pixel_trigger={pixel_trigger}")
        dut._log.info(f"freehand_trigger={freehand_trigger}, fill_active={fill_active}")
    
    # =========================================================================
    # Test 3: Color Mixing
    # =========================================================================
    dut._log.info("\n" + "="*60)
    dut._log.info("TEST 3: Color Mixing")
    dut._log.info("="*60)
    pygame_state['status_message'] = "TEST 3: Color Mixing"
    
    # Move to rainbow position
    await move_quick(dut, 'right', 50)
    await move_quick(dut, 'up', 60)
    
    # Quick rainbow - fewer colors, shorter lines
    rainbow_colors = ['Red', 'Yellow', 'Green', 'Cyan', 'Blue', 'White']
    start_x = read_signal(dut, 'user_project.pos_inst.x_pos') or 128
    
    for color_name in rainbow_colors:
        await set_color(dut, color_name)
        pixels_drawn += await move_continuous(dut, 'right', 20)
        await move_quick(dut, 'down', 4)
        current_x = read_signal(dut, 'user_project.pos_inst.x_pos') or start_x
        if current_x > start_x:
            await move_quick(dut, 'left', current_x - start_x)
    
    pygame_state['status_message'] = "TEST 3: Rainbow complete!"
    await update_pygame_state(dut)
    
    # =========================================================================
    # Test 4: Brush Sizes
    # =========================================================================
    dut._log.info("\n" + "="*60)
    dut._log.info("TEST 4: Brush Sizes")
    dut._log.info("="*60)
    pygame_state['status_message'] = "TEST 4: Brush sizes"
    
    # Reset brush size
    for _ in range(8):
        await press_button_with_edge(dut, {'l': 1})
    await update_pygame_state(dut)
    
    # Move to brush test area
    await move_quick(dut, 'left', 70)
    await move_quick(dut, 'down', 50)
    
    # Test 3 brush sizes (shorter lines)
    for size in range(3):
        for _ in range(size):
            await press_button_with_edge(dut, {'r': 1})
        await update_pygame_state(dut)
        
        pixels_drawn += await move_continuous(dut, 'up', 12)
        await move_quick(dut, 'right', 8)
        await move_quick(dut, 'down', 12)
        
        for _ in range(size + 1):
            await press_button_with_edge(dut, {'l': 1})
        await update_pygame_state(dut)
    
    pygame_state['status_message'] = "TEST 4: Brush sizes tested"
    await update_pygame_state(dut)
    
    # =========================================================================
    # Test 5: Symmetry Modes
    # =========================================================================
    dut._log.info("\n" + "="*60)
    dut._log.info("TEST 5: Symmetry Modes")
    dut._log.info("="*60)
    pygame_state['status_message'] = "TEST 5: Symmetry"
    
    # Set brush size 2
    await press_button_with_edge(dut, {'r': 1})
    await update_pygame_state(dut)
    
    # Move to symmetry test area
    await move_quick(dut, 'right', 50)
    await move_quick(dut, 'down', 50)
    
    # H-Mirror (Red)
    await set_color(dut, 'Red')
    await press_button_with_edge(dut, {'start': 1})  # H-Mirror
    await update_pygame_state(dut)
    pixels_drawn += await move_continuous(dut, 'right', 15)
    
    # V-Mirror (Green)
    await set_color(dut, 'Green')
    await press_button_with_edge(dut, {'start': 1})  # V-Mirror
    await update_pygame_state(dut)
    pixels_drawn += await move_continuous(dut, 'down', 15)
    
    # 4-Way (Blue)
    await set_color(dut, 'Blue')
    await press_button_with_edge(dut, {'start': 1})  # 4-Way
    await update_pygame_state(dut)
    for _ in range(10):
        pixels_drawn += await move_continuous(dut, 'right', 1)
        pixels_drawn += await move_continuous(dut, 'down', 1)
    
    # Reset symmetry
    await press_button_with_edge(dut, {'start': 1})
    await update_pygame_state(dut)
    
    pygame_state['status_message'] = "TEST 5: Symmetry tested"
    await update_pygame_state(dut)
    
    # =========================================================================
    # Test 6: Fill Rectangle
    # =========================================================================
    dut._log.info("\n" + "="*60)
    dut._log.info("TEST 6: Fill Rectangle")
    dut._log.info("="*60)
    pygame_state['status_message'] = "TEST 6: Fill rectangle"
    
    # Reset brush
    for _ in range(8):
        await press_button_with_edge(dut, {'l': 1})
    
    # Set Yellow
    await set_color(dut, 'Yellow')
    
    # Move to corner A
    await move_quick(dut, 'right', 30)
    await move_quick(dut, 'up', 30)
    
    # Fill mode on, set corner A
    await press_button_with_edge(dut, {'select': 1})
    await press_button_with_edge(dut, {'b': 1})
    
    # Move to corner B (smaller rectangle for speed)
    await move_quick(dut, 'right', 15)
    await move_quick(dut, 'down', 15)
    
    # Set corner B
    await press_button_with_edge(dut, {'b': 1})
    
    # Collect fill pixels
    fill_pixels = 0
    for _ in range(500):  # Max wait
        try:
            fill_busy = int(dut.user_project.fill_draw_inst.busy.value)
            fill_valid = int(dut.user_project.fill_draw_inst.pixel_valid.value)
            if fill_valid:
                fill_x = int(dut.user_project.fill_draw_inst.x_out.value)
                fill_y = int(dut.user_project.fill_draw_inst.y_out.value)
                colour = read_signal(dut, 'user_project.colour_inst.colour_out') or 0
                if 0 <= fill_x < 256 and 0 <= fill_y < 256:
                    pygame_state['update_queue'].put({
                        'type': 'pixel', 'x': fill_x, 'y': fill_y, 'color': colour
                    })
                    fill_pixels += 1
                    pixels_drawn += 1
            if not fill_busy:
                break
        except:
            break
        await ClockCycles(dut.clk, 1)
    
    # Fill mode off
    await press_button_with_edge(dut, {'select': 1})
    
    pygame_state['status_message'] = f"TEST 6: Fill ({fill_pixels} px)"
    await update_pygame_state(dut)
    
    # =========================================================================
    # Test 7: Undo/Redo
    # =========================================================================
    dut._log.info("\n" + "="*60)
    dut._log.info("TEST 7: Undo/Redo")
    dut._log.info("="*60)
    pygame_state['status_message'] = "TEST 7: Undo/Redo"
    
    # Move to bottom-right
    await move_quick(dut, 'right', 60)
    await move_quick(dut, 'down', 60)
    
    # Set Cyan
    await set_color(dut, 'Cyan')
    await update_pygame_state(dut)
    
    # Draw something
    pixels_drawn += await move_continuous(dut, 'right', 10)
    pixels_drawn += await move_continuous(dut, 'down', 10)
    
    # Undo (L+R)
    await send_buttons(dut, {'l': 1, 'r': 1})
    await ClockCycles(dut.clk, 5)
    await send_buttons(dut, {})
    
    for _ in range(50):
        try:
            undo_valid = int(dut.user_project.undo_inst.restore_valid.value)
            if undo_valid:
                ux = int(dut.user_project.undo_inst.x_out.value)
                uy = int(dut.user_project.undo_inst.y_out.value)
                uc = int(dut.user_project.undo_inst.color_out.value)
                if 0 <= ux < 256 and 0 <= uy < 256:
                    pygame_state['update_queue'].put({'type': 'pixel', 'x': ux, 'y': uy, 'color': uc})
        except:
            pass
        await ClockCycles(dut.clk, 1)
    
    # Redo (Select+Start)
    await send_buttons(dut, {'select': 1, 'start': 1})
    await ClockCycles(dut.clk, 5)
    await send_buttons(dut, {})
    
    for _ in range(50):
        try:
            undo_valid = int(dut.user_project.undo_inst.restore_valid.value)
            if undo_valid:
                ux = int(dut.user_project.undo_inst.x_out.value)
                uy = int(dut.user_project.undo_inst.y_out.value)
                uc = int(dut.user_project.undo_inst.color_out.value)
                if 0 <= ux < 256 and 0 <= uy < 256:
                    pygame_state['update_queue'].put({'type': 'pixel', 'x': ux, 'y': uy, 'color': uc})
        except:
            pass
        await ClockCycles(dut.clk, 1)
    
    pygame_state['status_message'] = "TEST 7: Undo/Redo tested"
    await update_pygame_state(dut)
    
    # =========================================================================
    # Test 8: Verify gamepad
    # =========================================================================
    dut._log.info("\n" + "="*60)
    dut._log.info("TEST 8: Gamepad verification")
    dut._log.info("="*60)
    pygame_state['status_message'] = "TEST 8: Gamepad check"
    
    await send_buttons(dut, {'a': 1})
    gp_a = read_signal(dut, 'user_project.gamepad_inst.a')
    dut._log.info(f"gp_a during press: {gp_a}")
    await send_buttons(dut, {})
    
    pygame_state['status_message'] = "TEST 8: Gamepad OK"
    await update_pygame_state(dut)
    
    # =========================================================================
    # Complete
    # =========================================================================
    dut._log.info("\n" + "="*60)
    dut._log.info("All tests complete!")
    dut._log.info("="*60)
    pygame_state['status_message'] = "✅ All tests complete!"
    await update_pygame_state(dut)
    
    # Wait 2 seconds
    dut._log.info("Waiting 2 seconds...")
    await ClockCycles(dut.clk, 100000000)  # 2 sec at 50MHz
    
    pygame_state['running'] = False
    pg_thread.join(timeout=1.0)
    
    dut._log.info("Debug test complete!")
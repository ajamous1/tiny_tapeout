#!/usr/bin/env python3
"""
Interactive Tiny Canvas Emulator
================================
A pygame-based visualization that actually drives the Verilog RTL simulation.

This emulator:
- Runs the actual Verilog code via cocotb + Icarus Verilog
- Sends gamepad button presses as serial PMOD protocol to the DUT
- Reads back position and status from the simulated hardware
- Displays results on a real-time canvas

Controls:
    Arrow Keys  - Move cursor (D-Pad)
    A key       - Toggle Red (Y button)
    S key       - Toggle Green (X button)  
    D key       - Toggle Blue (B button)
    SPACE       - Toggle Brush/Eraser (A button)
    C           - Clear canvas
    ESC/Q       - Quit

Run: python test/run_emulator.py gui   (standalone)
     python test/run_emulator.py sim   (with RTL simulation)
"""

import pygame
import sys
import os

# ============================================================================
# Colour Definitions (matches Verilog colour.v)
# ============================================================================
COLORS_RGB = {
    0b000: (0, 0, 0),         # Black
    0b001: (0, 0, 255),       # Blue
    0b010: (0, 255, 0),       # Green
    0b011: (0, 255, 255),     # Cyan (G+B)
    0b100: (255, 0, 0),       # Red
    0b101: (255, 0, 255),     # Magenta (R+B)
    0b110: (255, 255, 0),     # Yellow (R+G)
    0b111: (255, 255, 255),   # White (R+G+B)
}

COLOR_NAMES = {
    0b000: "Black", 0b001: "Blue", 0b010: "Green", 0b011: "Cyan",
    0b100: "Red", 0b101: "Magenta", 0b110: "Yellow", 0b111: "White"
}

# Gamepad PMOD button bit positions (directly from Verilog values)
BTN_B      = 0
BTN_Y      = 1
BTN_SELECT = 2
BTN_START  = 3
BTN_UP     = 4
BTN_DOWN   = 5
BTN_LEFT   = 6
BTN_RIGHT  = 7
BTN_A      = 8
BTN_X      = 9
BTN_L      = 10
BTN_R      = 11


class TinyCanvasEmulator:
    """
    Emulates the Tiny Canvas hardware with visual controller and I2C display.
    """
    
    def __init__(self, rtl_mode=False):
        pygame.init()
        
        self.rtl_mode = rtl_mode  # True = driving actual Verilog
        
        # Window setup
        self.width = 1200
        self.height = 800
        self.screen = pygame.display.set_mode((self.width, self.height))
        title = "Tiny Canvas - RTL Simulation" if rtl_mode else "Tiny Canvas - Emulator"
        pygame.display.set_caption(title)
        
        # Fonts
        self.font_title = pygame.font.Font(None, 42)
        self.font_large = pygame.font.Font(None, 32)
        self.font_medium = pygame.font.Font(None, 26)
        self.font_small = pygame.font.Font(None, 22)
        self.font_mono = pygame.font.SysFont("consolas", 20)
        
        # Colors
        self.bg_color = (20, 22, 30)
        self.panel_color = (35, 38, 50)
        self.text_color = (220, 220, 230)
        self.accent_color = (80, 180, 255)
        self.success_color = (80, 255, 120)
        self.warning_color = (255, 200, 80)
        self.rtl_color = (255, 100, 255)  # Purple for RTL mode
        
        # Canvas (256x256)
        self.canvas_size = 256
        self.canvas_scale = 2
        self.canvas = [[0 for _ in range(self.canvas_size)] for _ in range(self.canvas_size)]
        
        # Hardware state (mimics Verilog registers)
        self.x_pos = 128  # 8-bit position
        self.y_pos = 128  # 8-bit position
        self.sw_red = False
        self.sw_green = False
        self.sw_blue = False
        self.brush_mode = True  # True = Brush, False = Eraser
        
        # Button states (directly map to gamepad)
        self.btn_up = False
        self.btn_down = False
        self.btn_left = False
        self.btn_right = False
        self.btn_y = False  # Red toggle
        self.btn_x = False  # Green toggle
        self.btn_b = False  # Blue toggle
        self.btn_a = False  # Brush/Eraser toggle
        
        # For edge detection on toggle buttons
        self.prev_btn_y = False
        self.prev_btn_x = False
        self.prev_btn_b = False
        self.prev_btn_a = False
        
        # I2C transmission log
        self.i2c_log = []
        self.i2c_byte_count = 0
        self.sim_cycles = 0
        
        # Timing
        self.clock = pygame.time.Clock()
        self.move_timer = 0
        self.move_delay = 50  # ms between moves when holding
        
        self.running = True
    
    def get_gamepad_word(self):
        """
        Build the 12-bit gamepad word that would come from the PMOD.
        Active LOW (0 = pressed, 1 = released)
        """
        word = 0xFFF  # All released
        
        if self.btn_b:      word &= ~(1 << BTN_B)
        if self.btn_y:      word &= ~(1 << BTN_Y)
        if self.btn_up:     word &= ~(1 << BTN_UP)
        if self.btn_down:   word &= ~(1 << BTN_DOWN)
        if self.btn_left:   word &= ~(1 << BTN_LEFT)
        if self.btn_right:  word &= ~(1 << BTN_RIGHT)
        if self.btn_a:      word &= ~(1 << BTN_A)
        if self.btn_x:      word &= ~(1 << BTN_X)
        
        return word
    
    def get_colour_mix(self):
        """
        Implements colour mixing logic from colour.v
        In brush mode: combine RGB switches
        In eraser mode: always black
        """
        if self.brush_mode:
            return (int(self.sw_red) << 2) | (int(self.sw_green) << 1) | int(self.sw_blue)
        else:
            return 0b000  # Eraser = black
    
    def get_status_byte(self):
        """
        Build status byte matching Verilog project.v:
        [7]   = Up button
        [6]   = Down button
        [5]   = Left button
        [4]   = Right button
        [3]   = Brush mode (1=Brush, 0=Eraser)
        [2:0] = RGB colour
        """
        status = 0
        status |= int(self.btn_up) << 7
        status |= int(self.btn_down) << 6
        status |= int(self.btn_left) << 5
        status |= int(self.btn_right) << 4
        status |= int(self.brush_mode) << 3
        status |= self.get_colour_mix()
        return status
    
    def send_i2c_packet(self):
        """Simulate I2C transmission of x, y, status."""
        status = self.get_status_byte()
        self.i2c_byte_count += 3
        
        # Add to log
        colour = self.get_colour_mix()
        log_entry = {
            'x': self.x_pos,
            'y': self.y_pos,
            'status': status,
            'colour': colour,
            'colour_name': COLOR_NAMES[colour],
            'brush': self.brush_mode,
            'cycle': self.sim_cycles
        }
        self.i2c_log.insert(0, log_entry)
        
        # Keep only last 8 entries
        if len(self.i2c_log) > 8:
            self.i2c_log.pop()
    
    def should_paint(self):
        """
        Determine if we should paint based on mode and colour.
        - Brush mode + RGB=000: DON'T paint (just move)
        - Brush mode + RGB!=000: Paint the colour
        - Eraser mode: Paint black (to erase)
        """
        if self.brush_mode:
            # In brush mode, only paint if at least one colour is selected
            return self.sw_red or self.sw_green or self.sw_blue
        else:
            # In eraser mode, always paint (black)
            return True
    
    def paint_pixel(self):
        """Paint at current position based on mode and paint_enable."""
        if not self.should_paint():
            return  # Don't paint if RGB=000 in brush mode
        
        colour = self.get_colour_mix()
        if 0 <= self.x_pos < self.canvas_size and 0 <= self.y_pos < self.canvas_size:
            self.canvas[self.y_pos][self.x_pos] = colour
    
    def update_from_rtl(self, x_pos, y_pos, status):
        """Update state from RTL simulation outputs."""
        self.x_pos = x_pos
        self.y_pos = y_pos
        
        # Decode status byte
        self.brush_mode = bool((status >> 3) & 1)
        colour = status & 0b111
        self.sw_red = bool((colour >> 2) & 1)
        self.sw_green = bool((colour >> 1) & 1)
        self.sw_blue = bool(colour & 1)
        
        # Paint on canvas
        if 0 <= x_pos < self.canvas_size and 0 <= y_pos < self.canvas_size:
            self.canvas[y_pos][x_pos] = colour
        
        self.send_i2c_packet()
    
    def handle_input(self):
        """Handle keyboard input and update button states."""
        current_time = pygame.time.get_ticks()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    self.running = False
                elif event.key == pygame.K_c:  # Clear canvas
                    self.canvas = [[0 for _ in range(self.canvas_size)] for _ in range(self.canvas_size)]
                    self.i2c_log.clear()
                    self.i2c_byte_count = 0
                    print("CANVAS CLEARED")
        
        # Get current key states
        keys = pygame.key.get_pressed()
        
        # D-pad (directly held)
        self.btn_up = keys[pygame.K_UP]
        self.btn_down = keys[pygame.K_DOWN]
        self.btn_left = keys[pygame.K_LEFT]
        self.btn_right = keys[pygame.K_RIGHT]
        
        # Toggle buttons (detect edges)
        self.btn_y = keys[pygame.K_a]  # Y = Red
        self.btn_x = keys[pygame.K_s]  # X = Green
        self.btn_b = keys[pygame.K_d]  # B = Blue
        self.btn_a = keys[pygame.K_SPACE]  # A = Brush/Eraser
        
        # Edge detection for toggles (only in non-RTL mode)
        if not self.rtl_mode:
            # Y button - toggle Red
            if self.btn_y and not self.prev_btn_y:
                self.sw_red = not self.sw_red
                print(f"RED: {'ON' if self.sw_red else 'OFF'}")
            
            # X button - toggle Green
            if self.btn_x and not self.prev_btn_x:
                self.sw_green = not self.sw_green
                print(f"GREEN: {'ON' if self.sw_green else 'OFF'}")
            
            # B button - toggle Blue
            if self.btn_b and not self.prev_btn_b:
                self.sw_blue = not self.sw_blue
                print(f"BLUE: {'ON' if self.sw_blue else 'OFF'}")
            
            # A button - toggle Brush/Eraser
            if self.btn_a and not self.prev_btn_a:
                self.brush_mode = not self.brush_mode
                print(f"MODE: {'BRUSH' if self.brush_mode else 'ERASER'}")
            
            # Movement (with delay for held keys)
            if current_time - self.move_timer > self.move_delay:
                moved = False
                
                if self.btn_up and self.y_pos < 255:
                    self.y_pos += 1
                    moved = True
                elif self.btn_down and self.y_pos > 0:
                    self.y_pos -= 1
                    moved = True
                
                if self.btn_right and self.x_pos < 255:
                    self.x_pos += 1
                    moved = True
                elif self.btn_left and self.x_pos > 0:
                    self.x_pos -= 1
                    moved = True
                
                if moved:
                    self.move_timer = current_time
                    self.paint_pixel()
                    self.send_i2c_packet()
        
        # Store previous states for edge detection
        self.prev_btn_y = self.btn_y
        self.prev_btn_x = self.btn_x
        self.prev_btn_b = self.btn_b
        self.prev_btn_a = self.btn_a
    
    def draw_controller(self):
        """Draw simplified controller with only used buttons."""
        x, y = 50, 480
        
        # Panel background
        panel_rect = pygame.Rect(x - 20, y - 60, 380, 300)
        pygame.draw.rect(self.screen, self.panel_color, panel_rect, border_radius=15)
        
        # Title
        title = self.font_large.render("CONTROLLER", True, self.accent_color)
        self.screen.blit(title, (x, y - 50))
        
        # D-Pad
        dpad_x, dpad_y = x + 80, y + 60
        dpad_size = 35
        
        # D-pad background
        pygame.draw.rect(self.screen, (40, 42, 55), 
                        (dpad_x - dpad_size - 5, dpad_y - 10, dpad_size*2 + 10, 20), border_radius=3)
        pygame.draw.rect(self.screen, (40, 42, 55),
                        (dpad_x - 10, dpad_y - dpad_size - 5, 20, dpad_size*2 + 10), border_radius=3)
        
        # Direction buttons
        btn_colors = {
            'up': (100, 255, 100) if self.btn_up else (60, 62, 75),
            'down': (100, 255, 100) if self.btn_down else (60, 62, 75),
            'left': (100, 255, 100) if self.btn_left else (60, 62, 75),
            'right': (100, 255, 100) if self.btn_right else (60, 62, 75),
        }
        
        pygame.draw.rect(self.screen, btn_colors['up'], (dpad_x-12, dpad_y-dpad_size, 24, 22), border_radius=4)
        pygame.draw.rect(self.screen, btn_colors['down'], (dpad_x-12, dpad_y+dpad_size-22, 24, 22), border_radius=4)
        pygame.draw.rect(self.screen, btn_colors['left'], (dpad_x-dpad_size, dpad_y-10, 22, 20), border_radius=4)
        pygame.draw.rect(self.screen, btn_colors['right'], (dpad_x+dpad_size-22, dpad_y-10, 22, 20), border_radius=4)
        
        # Arrow symbols
        arrows = [("▲", dpad_x-5, dpad_y-dpad_size+3), ("▼", dpad_x-5, dpad_y+dpad_size-20),
                  ("◄", dpad_x-dpad_size+5, dpad_y-8), ("►", dpad_x+dpad_size-17, dpad_y-8)]
        for sym, ax, ay in arrows:
            arr = self.font_small.render(sym, True, (200, 200, 200))
            self.screen.blit(arr, (ax, ay))
        
        # Face buttons
        btn_x_pos, btn_y_pos = x + 280, y + 60
        btn_r = 25
        spacing = 50
        
        # Y button (top) - RED toggle
        y_color = (255, 80, 80) if self.sw_red else (100, 40, 40)
        y_border = (255, 255, 100) if self.btn_y else (255, 255, 255)
        pygame.draw.circle(self.screen, y_color, (btn_x_pos, btn_y_pos - spacing//2), btn_r)
        pygame.draw.circle(self.screen, y_border, (btn_x_pos, btn_y_pos - spacing//2), btn_r, 3 if self.btn_y else 2)
        lbl = self.font_medium.render("Y", True, (255, 255, 255))
        self.screen.blit(lbl, (btn_x_pos - 6, btn_y_pos - spacing//2 - 10))
        
        # X button (left) - GREEN toggle
        x_color = (80, 255, 80) if self.sw_green else (40, 100, 40)
        x_border = (255, 255, 100) if self.btn_x else (255, 255, 255)
        pygame.draw.circle(self.screen, x_color, (btn_x_pos - spacing//2, btn_y_pos + spacing//4), btn_r)
        pygame.draw.circle(self.screen, x_border, (btn_x_pos - spacing//2, btn_y_pos + spacing//4), btn_r, 3 if self.btn_x else 2)
        lbl = self.font_medium.render("X", True, (255, 255, 255))
        self.screen.blit(lbl, (btn_x_pos - spacing//2 - 6, btn_y_pos + spacing//4 - 10))
        
        # B button (right) - BLUE toggle
        b_color = (80, 80, 255) if self.sw_blue else (40, 40, 100)
        b_border = (255, 255, 100) if self.btn_b else (255, 255, 255)
        pygame.draw.circle(self.screen, b_color, (btn_x_pos + spacing//2, btn_y_pos + spacing//4), btn_r)
        pygame.draw.circle(self.screen, b_border, (btn_x_pos + spacing//2, btn_y_pos + spacing//4), btn_r, 3 if self.btn_b else 2)
        lbl = self.font_medium.render("B", True, (255, 255, 255))
        self.screen.blit(lbl, (btn_x_pos + spacing//2 - 6, btn_y_pos + spacing//4 - 10))
        
        # A button (bottom) - BRUSH/ERASER toggle
        a_color = (80, 200, 80) if self.brush_mode else (200, 80, 80)
        a_border = (255, 255, 100) if self.btn_a else (255, 255, 255)
        pygame.draw.circle(self.screen, a_color, (btn_x_pos, btn_y_pos + spacing), btn_r)
        pygame.draw.circle(self.screen, a_border, (btn_x_pos, btn_y_pos + spacing), btn_r, 3 if self.btn_a else 2)
        lbl = self.font_medium.render("A", True, (255, 255, 255))
        self.screen.blit(lbl, (btn_x_pos - 6, btn_y_pos + spacing - 10))
        
        # Key bindings
        bindings_y = y + 150
        bindings = [
            ("↑↓←→", "Move Cursor", self.text_color),
            ("A", f"RED {'●' if self.sw_red else '○'}", (255, 100, 100) if self.sw_red else (150, 150, 150)),
            ("S", f"GREEN {'●' if self.sw_green else '○'}", (100, 255, 100) if self.sw_green else (150, 150, 150)),
            ("D", f"BLUE {'●' if self.sw_blue else '○'}", (100, 100, 255) if self.sw_blue else (150, 150, 150)),
            ("SPACE", f"{'BRUSH' if self.brush_mode else 'ERASER'}", self.success_color if self.brush_mode else self.warning_color),
            ("C", "Clear", (150, 150, 150)),
        ]
        
        for i, (key, action, color) in enumerate(bindings):
            key_lbl = self.font_small.render(f"{key}:", True, (150, 150, 150))
            act_lbl = self.font_small.render(action, True, color)
            self.screen.blit(key_lbl, (x + (i % 3) * 120, bindings_y + (i // 3) * 22))
            self.screen.blit(act_lbl, (x + 55 + (i % 3) * 120, bindings_y + (i // 3) * 22))
    
    def draw_canvas(self):
        """Draw the 256x256 pixel canvas."""
        canvas_x, canvas_y = 450, 80
        scale = self.canvas_scale
        size = self.canvas_size * scale
        
        # Border
        border_color = self.rtl_color if self.rtl_mode else (60, 65, 80)
        pygame.draw.rect(self.screen, border_color, (canvas_x - 4, canvas_y - 4, size + 8, size + 8), border_radius=5)
        
        # Create and draw canvas surface
        surf = pygame.Surface((self.canvas_size, self.canvas_size))
        for cy in range(self.canvas_size):
            for cx in range(self.canvas_size):
                color = COLORS_RGB[self.canvas[cy][cx]]
                surf.set_at((cx, self.canvas_size - 1 - cy), color)
        
        scaled = pygame.transform.scale(surf, (size, size))
        self.screen.blit(scaled, (canvas_x, canvas_y))
        
        # Cursor
        cursor_x = canvas_x + self.x_pos * scale + scale // 2
        cursor_y = canvas_y + (self.canvas_size - 1 - self.y_pos) * scale + scale // 2
        cursor_size = max(scale * 3, 10)
        
        pygame.draw.rect(self.screen, (255, 255, 0), 
                        (cursor_x - cursor_size//2, cursor_y - cursor_size//2, cursor_size, cursor_size), 2)
    
    def draw_i2c_panel(self):
        """Draw I2C communication details panel."""
        x, y = 450, 620
        
        # Panel background
        panel_rect = pygame.Rect(x - 10, y - 10, 720, 170)
        pygame.draw.rect(self.screen, self.panel_color, panel_rect, border_radius=10)
        
        # Title with mode indicator
        title_color = self.rtl_color if self.rtl_mode else self.accent_color
        mode_str = "I2C FROM RTL" if self.rtl_mode else "I2C EMULATED"
        title = self.font_large.render(mode_str, True, title_color)
        self.screen.blit(title, (x, y))
        
        # Current packet info
        status = self.get_status_byte()
        colour = self.get_colour_mix()
        
        info_y = y + 35
        
        # Byte breakdown
        byte_info = [
            f"Byte 1 (X):      0x{self.x_pos:02X} = {self.x_pos:3d}",
            f"Byte 2 (Y):      0x{self.y_pos:02X} = {self.y_pos:3d}",
            f"Byte 3 (Status): 0x{status:02X} = {status:08b}b",
        ]
        
        for i, info in enumerate(byte_info):
            lbl = self.font_mono.render(info, True, self.warning_color)
            self.screen.blit(lbl, (x, info_y + i * 24))
        
        # Status byte breakdown
        breakdown_x = x + 350
        breakdown = [
            f"[7:4] Buttons: {(status >> 4) & 0xF:04b}",
            f"[3]   Brush:   {(status >> 3) & 1} ({'ON' if self.brush_mode else 'OFF'})",
            f"[2:0] RGB:     {colour:03b} = {COLOR_NAMES[colour]}",
        ]
        
        for i, info in enumerate(breakdown):
            lbl = self.font_mono.render(info, True, (180, 180, 180))
            self.screen.blit(lbl, (breakdown_x, info_y + i * 24))
        
        # Stats
        stats_y = info_y + 85
        stats = f"Bytes: {self.i2c_byte_count} | Packets: {self.i2c_byte_count // 3}"
        if self.rtl_mode:
            stats += f" | Sim Cycles: {self.sim_cycles}"
        stats_lbl = self.font_small.render(stats, True, (150, 150, 150))
        self.screen.blit(stats_lbl, (x, stats_y))
        
        # Recent I2C log
        if self.i2c_log:
            log_x = x + 350
            log_title = self.font_small.render("Recent I2C:", True, (150, 150, 150))
            self.screen.blit(log_title, (log_x, stats_y))
            
            for i, entry in enumerate(self.i2c_log[:3]):
                log_text = f"({entry['x']},{entry['y']}) {entry['colour_name']}"
                log_lbl = self.font_small.render(log_text, True, (120, 120, 140))
                self.screen.blit(log_lbl, (log_x + 100 + i * 130, stats_y))
    
    def draw_colour_preview(self):
        """Draw current colour preview."""
        x, y = 50, 80
        
        # Panel
        panel_rect = pygame.Rect(x - 20, y - 20, 380, 380)
        pygame.draw.rect(self.screen, self.panel_color, panel_rect, border_radius=15)
        
        # Title
        title = self.font_large.render("COLOUR OUTPUT", True, self.accent_color)
        self.screen.blit(title, (x, y))
        
        # Large colour preview
        colour = self.get_colour_mix()
        preview_rect = pygame.Rect(x, y + 40, 150, 150)
        pygame.draw.rect(self.screen, COLORS_RGB[colour], preview_rect, border_radius=10)
        pygame.draw.rect(self.screen, (100, 100, 100), preview_rect, 3, border_radius=10)
        
        # Colour name
        name = COLOR_NAMES[colour]
        name_lbl = self.font_large.render(name, True, self.text_color)
        self.screen.blit(name_lbl, (x + 160, y + 50))
        
        # RGB value
        rgb_lbl = self.font_mono.render(f"RGB: {colour:03b}", True, (180, 180, 180))
        self.screen.blit(rgb_lbl, (x + 160, y + 85))
        
        # Position
        pos_lbl = self.font_mono.render(f"Pos: ({self.x_pos}, {self.y_pos})", True, (180, 180, 180))
        self.screen.blit(pos_lbl, (x + 160, y + 110))
        
        # Mode
        mode_text = "BRUSH MODE" if self.brush_mode else "ERASER MODE"
        mode_color = self.success_color if self.brush_mode else self.warning_color
        mode_lbl = self.font_medium.render(mode_text, True, mode_color)
        self.screen.blit(mode_lbl, (x + 160, y + 140))
        
        # RGB switch status
        switch_y = y + 200
        switches = [
            ("R", self.sw_red, (255, 0, 0)),
            ("G", self.sw_green, (0, 255, 0)),
            ("B", self.sw_blue, (0, 0, 255)),
        ]
        
        for i, (label, state, color) in enumerate(switches):
            sx = x + i * 120
            
            bg_color = color if state else (50, 50, 50)
            pygame.draw.rect(self.screen, bg_color, (sx, switch_y, 100, 50), border_radius=8)
            pygame.draw.rect(self.screen, (150, 150, 150), (sx, switch_y, 100, 50), 2, border_radius=8)
            
            lbl = self.font_large.render(label, True, (255, 255, 255) if state else (100, 100, 100))
            self.screen.blit(lbl, (sx + 10, switch_y + 10))
            
            status_text = "ON" if state else "OFF"
            status_lbl = self.font_small.render(status_text, True, (255, 255, 255) if state else (100, 100, 100))
            self.screen.blit(status_lbl, (sx + 55, switch_y + 15))
        
        # Colour mixing guide
        guide_y = y + 270
        guide_title = self.font_medium.render("Colour Mixing:", True, self.text_color)
        self.screen.blit(guide_title, (x, guide_y))
        
        guide_items = [
            "R→Red    R+G→Yellow",
            "G→Green  R+B→Magenta", 
            "B→Blue   G+B→Cyan",
            "         RGB→White",
        ]
        
        for i, item in enumerate(guide_items):
            lbl = self.font_small.render(item, True, (150, 150, 150))
            self.screen.blit(lbl, (x, guide_y + 25 + i * 18))
    
    def draw_header(self):
        """Draw header."""
        title = self.font_title.render("TINY CANVAS", True, self.accent_color)
        self.screen.blit(title, (450, 20))
        
        if self.rtl_mode:
            subtitle = self.font_small.render("● LIVE RTL SIMULATION - Actual Verilog Running!", True, self.rtl_color)
        else:
            subtitle = self.font_small.render("Emulator Mode - Simulating Hardware Logic", True, (120, 120, 140))
        self.screen.blit(subtitle, (450, 55))
    
    def draw(self):
        """Main draw function."""
        self.screen.fill(self.bg_color)
        self.draw_header()
        self.draw_colour_preview()
        self.draw_controller()
        self.draw_canvas()
        self.draw_i2c_panel()
        pygame.display.flip()
    
    def run(self):
        """Main loop for standalone mode."""
        print("\n" + "=" * 50)
        print("TINY CANVAS EMULATOR STARTED")
        print("=" * 50)
        print("\nControls:")
        print("  Arrow Keys  - Move cursor")
        print("  A           - Toggle RED")
        print("  S           - Toggle GREEN")
        print("  D           - Toggle BLUE")
        print("  SPACE       - Toggle Brush/Eraser")
        print("  C           - Clear canvas")
        print("  ESC/Q       - Quit")
        print("=" * 50 + "\n")
        
        # Initial I2C packet
        self.send_i2c_packet()
        
        while self.running:
            self.handle_input()
            self.draw()
            self.clock.tick(60)
        
        pygame.quit()
        print("\nEmulator closed.")


# ============================================================================
# Cocotb RTL Simulation Test
# ============================================================================
try:
    import cocotb
    from cocotb.clock import Clock
    from cocotb.triggers import ClockCycles, Timer, RisingEdge
    
    @cocotb.test()
    async def interactive_rtl_test(dut):
        """Interactive test that drives actual Verilog RTL with pygame GUI."""
        
        dut._log.info("=" * 60)
        dut._log.info("INTERACTIVE RTL SIMULATION")
        dut._log.info("=" * 60)
        
        # Initialize pygame GUI in RTL mode
        gui = TinyCanvasEmulator(rtl_mode=True)
        
        # Start system clock (50 MHz = 20ns period)
        clock = Clock(dut.clk, 20, units="ns")
        cocotb.start_soon(clock.start())
        
        # Reset
        dut._log.info("Resetting DUT...")
        dut.ena.value = 1
        dut.rst_n.value = 0
        dut.ui_in.value = 0
        dut.uio_in.value = 0b0110  # SDA=1, SCL=1 idle
        await ClockCycles(dut.clk, 20)
        dut.rst_n.value = 1
        await ClockCycles(dut.clk, 10)
        
        dut._log.info("RTL Ready - Starting interactive loop")
        dut._log.info("Use keyboard to control. Press ESC to quit.")
        
        async def send_gamepad_frame(word):
            """Send 12-bit gamepad data via PMOD serial protocol."""
            # pmod_data = ui_in[0], pmod_clk = ui_in[1], pmod_latch = ui_in[2]
            
            # Send 12 bits MSB first
            for i in range(11, -1, -1):
                bit = (word >> i) & 1
                
                # Set data bit, clock low
                current = int(dut.ui_in.value) & 0xF8  # Preserve upper bits
                dut.ui_in.value = current | (bit << 0) | (0 << 1) | (0 << 2)
                await ClockCycles(dut.clk, 5)
                
                # Clock high (data sampled)
                dut.ui_in.value = current | (bit << 0) | (1 << 1) | (0 << 2)
                await ClockCycles(dut.clk, 5)
                
                # Clock low
                dut.ui_in.value = current | (bit << 0) | (0 << 1) | (0 << 2)
                await ClockCycles(dut.clk, 3)
            
            # Latch pulse
            current = int(dut.ui_in.value) & 0xF8
            dut.ui_in.value = current | (1 << 2)  # Latch high
            await ClockCycles(dut.clk, 5)
            dut.ui_in.value = current | (0 << 2)  # Latch low
            await ClockCycles(dut.clk, 5)
        
        frame_count = 0
        last_gamepad_word = 0xFFF
        
        try:
            while gui.running:
                # Process pygame events
                gui.handle_input()
                
                # Get gamepad state from GUI
                gamepad_word = gui.get_gamepad_word()
                
                # Send gamepad frame to DUT if state changed or periodically
                if gamepad_word != last_gamepad_word or frame_count % 10 == 0:
                    await send_gamepad_frame(gamepad_word)
                    last_gamepad_word = gamepad_word
                
                # Let simulation advance
                await ClockCycles(dut.clk, 100)
                gui.sim_cycles += 100
                
                # Try to read position from internal signals if accessible
                # (This depends on the testbench exposing these signals)
                try:
                    # Read from the position module via hierarchy
                    x_val = int(dut.user_project.pos_inst.x_pos.value)
                    y_val = int(dut.user_project.pos_inst.y_pos.value)
                    
                    # Read colour output
                    colour_val = int(dut.user_project.colour_inst.colour_out.value)
                    
                    # Read brush mode
                    brush_val = int(dut.user_project.brush_mode.value)
                    
                    # Build status byte
                    status = (brush_val << 3) | colour_val
                    
                    # Update GUI from RTL values
                    gui.update_from_rtl(x_val, y_val, status)
                    
                except Exception:
                    # If we can't read internal signals, use emulated values
                    pass
                
                # Draw GUI
                gui.draw()
                gui.clock.tick(30)  # 30 FPS for GUI
                
                frame_count += 1
                
        except KeyboardInterrupt:
            dut._log.info("Interrupted by user")
        
        finally:
            pygame.quit()
        
        dut._log.info(f"Simulation complete. Ran {gui.sim_cycles} cycles.")

except ImportError:
    # cocotb not available, standalone mode only
    pass


def main():
    """Entry point for standalone mode."""
    emu = TinyCanvasEmulator(rtl_mode=False)
    emu.run()


if __name__ == "__main__":
    main()

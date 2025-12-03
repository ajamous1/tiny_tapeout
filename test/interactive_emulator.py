#!/usr/bin/env python3
"""
Interactive Tiny Canvas Emulator
================================
A pygame-based visualization for the Tiny Canvas MS Paint-style project.

Controls:
    Arrow Keys  - Move cursor (D-Pad)
    R           - Toggle Red
    G           - Toggle Green  
    B           - Toggle Blue
    SPACE       - Toggle Brush/Eraser mode
    I           - Keyboard Input Mode
    C           - Clear canvas
    ESC/Q       - Quit
"""

import pygame
import sys
import os

# ============================================================================
# Colour Definitions (matches Verilog colour.v)
# ============================================================================
COLORS = {
    0b000: (0, 0, 0),         # Black/None
    0b100: (255, 0, 0),       # Red
    0b010: (0, 255, 0),       # Green
    0b001: (0, 0, 255),       # Blue
    0b110: (255, 255, 0),     # Yellow (R+G)
    0b101: (255, 0, 255),     # Magenta (R+B)
    0b011: (0, 255, 255),     # Cyan (G+B)
    0b111: (255, 255, 255),   # White (R+G+B)
}

COLOR_NAMES = {
    0b000: "Black", 0b001: "Blue", 0b010: "Green", 0b011: "Cyan",
    0b100: "Red", 0b101: "Magenta", 0b110: "Yellow", 0b111: "White"
}


class TinyCanvas:
    """Emulates the Tiny Canvas hardware logic."""
    
    def __init__(self):
        # Hardware state
        self.btn_up = False
        self.btn_down = False
        self.btn_right = False
        self.btn_left = False
        self.sw_red = False
        self.sw_green = False
        self.sw_blue = False
        self.sw_brush = True  # Start in brush mode
        
        # Canvas state (256x256 grid, each cell stores 3-bit color)
        self.grid_size = 256
        self.canvas = [[0 for _ in range(self.grid_size)] for _ in range(self.grid_size)]
        
        # Cursor position (start at center)
        self.cursor_x = 0
        self.cursor_y = 0
        
        # For handling button press timing
        self.last_move_time = 0
        self.move_delay = 50  # milliseconds between moves
        
        # I2C communication state
        self.i2c_buffer = []
        self.i2c_x = 0
        self.i2c_y = 0
        self.i2c_status = 0
        self.i2c_last_state = None
        self.external_commands_received = 0
        
        # Keyboard input mode
        self.keyboard_input_mode = False
        self.keyboard_input_buffer = ""
        self.keyboard_command_status = ""
        
    def get_color_mix(self):
        """
        Implements the color mixing logic from colour.v module.
        In brush mode: combine RGB switches
        In eraser mode: always black
        """
        if self.sw_brush:
            rgb_sel = (self.sw_red << 2) | (self.sw_green << 1) | self.sw_blue
            return rgb_sel
        else:
            return 0b000  # Eraser mode = black
    
    def should_paint(self):
        """
        Determine if we should paint based on mode and colour.
        - Brush mode + RGB=000: DON'T paint (just move)
        - Brush mode + RGB!=000: Paint the colour
        - Eraser mode: Paint black (to erase)
        """
        if self.sw_brush:
            return self.sw_red or self.sw_green or self.sw_blue
        else:
            return True  # Eraser always paints (black)
    
    def get_status(self):
        """
        Emulates the status output matching hardware pinout.
        Status Byte [7:0]:
          [7] = Up button
          [6] = Down button
          [5] = Left button
          [4] = Right button
          [3] = Brush/Eraser (1=Brush, 0=Eraser)
          [2:0] = RGB Color
        """
        status = 0
        status |= (1 if self.btn_up else 0) << 7
        status |= (1 if self.btn_down else 0) << 6
        status |= (1 if self.btn_left else 0) << 5
        status |= (1 if self.btn_right else 0) << 4
        status |= (1 if self.sw_brush else 0) << 3
        status |= self.get_color_mix()
        return status
    
    def update_cursor(self, current_time):
        """Update cursor position based on button presses."""
        if current_time - self.last_move_time < self.move_delay:
            return False
        
        moved = False
        if self.btn_up and self.cursor_y < self.grid_size - 1:
            self.cursor_y += 1
            moved = True
        elif self.btn_down and self.cursor_y > 0:
            self.cursor_y -= 1
            moved = True
        elif self.btn_left and self.cursor_x > 0:
            self.cursor_x -= 1
            moved = True
        elif self.btn_right and self.cursor_x < self.grid_size - 1:
            self.cursor_x += 1
            moved = True
        
        if moved:
            self.last_move_time = current_time
            # Paint if we should
            if self.should_paint():
                canvas_y = self.cursor_y
                self.canvas[canvas_y][self.cursor_x] = self.get_color_mix()
        
        return moved
    
    def auto_send_i2c_if_changed(self):
        """Automatically send I2C command when state changes."""
        current_state = (self.cursor_x, self.cursor_y, self.get_status())
        
        if current_state != self.i2c_last_state:
            self.i2c_last_state = current_state
            x, y, status = current_state
            self.i2c_receive_byte(x)
            self.i2c_receive_byte(y)
            self.i2c_receive_byte(status)
    
    def clear_canvas(self):
        """Clear the entire canvas."""
        self.canvas = [[0 for _ in range(self.grid_size)] for _ in range(self.grid_size)]
        self.i2c_buffer = []
        self.external_commands_received = 0
    
    def i2c_receive_byte(self, byte_val):
        """
        Simulate I2C byte reception.
        Accepts 3 bytes at a time: X, Y, Status
        """
        self.i2c_buffer.append(byte_val)
        
        if len(self.i2c_buffer) >= 3:
            self.i2c_x = self.i2c_buffer[0]
            self.i2c_y = self.i2c_buffer[1]
            self.i2c_status = self.i2c_buffer[2]
            
            # Extract brush/eraser mode from status byte (bit [3])
            is_brush_mode = (self.i2c_status >> 3) & 1
            
            # Extract color from status byte (bits [2:0] = RGB)
            color_mix = self.i2c_status & 0b111
            
            # If in eraser mode, always output black
            if not is_brush_mode:
                color_mix = 0b000
            
            # Only paint if should_paint logic passes
            # Brush mode with color=000 should NOT paint
            should_paint = True
            if is_brush_mode and color_mix == 0:
                should_paint = False
            
            # Paint at the specified position
            if should_paint and 0 <= self.i2c_x < self.grid_size and 0 <= self.i2c_y < self.grid_size:
                self.canvas[self.i2c_y][self.i2c_x] = color_mix
            
            self.i2c_buffer = []


class CanvasEmulator:
    """Pygame-based GUI for the Tiny Canvas emulator."""
    
    def __init__(self):
        pygame.init()
        
        # Get screen info
        info = pygame.display.Info()
        screen_width = info.current_w
        screen_height = info.current_h
        
        # Use 80% of screen size
        window_width = int(screen_width * 0.80)
        window_height = int(screen_height * 0.80)
        
        # Create resizable window
        self.screen = pygame.display.set_mode((window_width, window_height), pygame.RESIZABLE)
        pygame.display.set_caption("Tiny Canvas Emulator - 256x256")
        
        # Grid setup
        self.grid_size = 256
        
        # Reserve space for sidebar
        self.sidebar_width = min(350, int(window_width * 0.28))
        
        # Calculate cell size
        available_width = window_width - self.sidebar_width - 60
        available_height = window_height - 120
        
        max_cell_w = available_width // self.grid_size
        max_cell_h = available_height // self.grid_size
        self.cell_size = min(max_cell_w, max_cell_h)
        self.cell_size = max(self.cell_size, 2)
        
        self.canvas_width = self.cell_size * self.grid_size
        self.canvas_height = self.cell_size * self.grid_size
        
        # Center the canvas
        self.canvas_offset_x = (window_width - self.sidebar_width - self.canvas_width) // 2
        self.canvas_offset_y = (window_height - self.canvas_height) // 2 + 40
        
        # Colors for UI
        self.bg_color = (30, 35, 45)
        self.panel_color = (40, 45, 55)
        self.text_color = (220, 220, 220)
        self.accent_color = (80, 200, 255)
        
        # Screen dimensions
        self.window_width = window_width
        self.window_height = window_height
        
        # Fonts
        self.font_title = pygame.font.Font(None, 36)
        self.font_large = pygame.font.Font(None, 32)
        self.font_medium = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 20)
        
        # Canvas logic
        self.canvas = TinyCanvas()
        
        # Clock
        self.clock = pygame.time.Clock()
        self.fps = 60
    
    def recalculate_layout(self, window_width, window_height):
        """Recalculate layout when window is resized."""
        self.window_width = window_width
        self.window_height = window_height
        
        self.sidebar_width = min(350, int(window_width * 0.28))
        
        available_width = window_width - self.sidebar_width - 60
        available_height = window_height - 120
        
        max_cell_w = available_width // self.grid_size
        max_cell_h = available_height // self.grid_size
        self.cell_size = min(max_cell_w, max_cell_h)
        self.cell_size = max(self.cell_size, 1)
        
        self.canvas_width = self.cell_size * self.grid_size
        self.canvas_height = self.cell_size * self.grid_size
        
        self.canvas_offset_x = (window_width - self.sidebar_width - self.canvas_width) // 2
        self.canvas_offset_y = (window_height - self.canvas_height) // 2 + 40
        
    def handle_events(self):
        """Handle keyboard input."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            if event.type == pygame.VIDEORESIZE:
                self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                self.recalculate_layout(event.w, event.h)
            
            if event.type == pygame.KEYDOWN:
                if self.canvas.keyboard_input_mode:
                    if event.key == pygame.K_RETURN:
                        self.process_keyboard_command()
                    elif event.key == pygame.K_ESCAPE:
                        self.canvas.keyboard_input_mode = False
                        self.canvas.keyboard_input_buffer = ""
                        self.canvas.keyboard_command_status = ""
                    elif event.key == pygame.K_BACKSPACE:
                        self.canvas.keyboard_input_buffer = self.canvas.keyboard_input_buffer[:-1]
                    else:
                        if event.unicode and (event.unicode.isprintable() or event.unicode == ' '):
                            self.canvas.keyboard_input_buffer += event.unicode
                else:
                    if event.key == pygame.K_i:
                        self.canvas.keyboard_input_mode = True
                        self.canvas.keyboard_input_buffer = ""
                        self.canvas.keyboard_command_status = "Format: STATUS or X Y STATUS"
                    elif event.key == pygame.K_r:
                        self.canvas.sw_red = not self.canvas.sw_red
                        print(f"RED: {'ON' if self.canvas.sw_red else 'OFF'}")
                    elif event.key == pygame.K_g:
                        self.canvas.sw_green = not self.canvas.sw_green
                        print(f"GREEN: {'ON' if self.canvas.sw_green else 'OFF'}")
                    elif event.key == pygame.K_b:
                        self.canvas.sw_blue = not self.canvas.sw_blue
                        print(f"BLUE: {'ON' if self.canvas.sw_blue else 'OFF'}")
                    elif event.key == pygame.K_SPACE:
                        self.canvas.sw_brush = not self.canvas.sw_brush
                        print(f"MODE: {'BRUSH' if self.canvas.sw_brush else 'ERASER'}")
                    elif event.key == pygame.K_c:
                        self.canvas.clear_canvas()
                        print("Canvas cleared!")
                    elif event.key in (pygame.K_ESCAPE, pygame.K_q):
                        return False
        
        # Handle arrow keys (held down)
        if not self.canvas.keyboard_input_mode:
            keys = pygame.key.get_pressed()
            self.canvas.btn_up = keys[pygame.K_UP]
            self.canvas.btn_down = keys[pygame.K_DOWN]
            self.canvas.btn_left = keys[pygame.K_LEFT]
            self.canvas.btn_right = keys[pygame.K_RIGHT]
        else:
            self.canvas.btn_up = False
            self.canvas.btn_down = False
            self.canvas.btn_left = False
            self.canvas.btn_right = False
        
        return True
    
    def process_keyboard_command(self):
        """Parse and execute a keyboard command."""
        try:
            parts = self.canvas.keyboard_input_buffer.strip().split()
            
            if len(parts) == 1:
                # Single byte mode: STATUS
                input_str = parts[0]
                if input_str.startswith('0x') or input_str.startswith('0X'):
                    status = int(input_str, 16)
                else:
                    status = int(input_str)
                
                if not (0 <= status <= 255):
                    self.canvas.keyboard_command_status = "Error: Value must be 0-255"
                    return
                
                # Decode and apply
                btn_up = (status >> 7) & 1
                btn_down = (status >> 6) & 1
                btn_left = (status >> 5) & 1
                btn_right = (status >> 4) & 1
                brush = (status >> 3) & 1
                color = status & 0b111
                
                self.canvas.sw_brush = bool(brush)
                self.canvas.sw_red = bool((color >> 2) & 1)
                self.canvas.sw_green = bool((color >> 1) & 1)
                self.canvas.sw_blue = bool(color & 1)
                
                # Move cursor
                if btn_up and self.canvas.cursor_y < self.canvas.grid_size - 1:
                    self.canvas.cursor_y += 1
                elif btn_down and self.canvas.cursor_y > 0:
                    self.canvas.cursor_y -= 1
                elif btn_left and self.canvas.cursor_x > 0:
                    self.canvas.cursor_x -= 1
                elif btn_right and self.canvas.cursor_x < self.canvas.grid_size - 1:
                    self.canvas.cursor_x += 1
                
                # Paint if should_paint
                if self.canvas.should_paint():
                    self.canvas.canvas[self.canvas.cursor_y][self.canvas.cursor_x] = self.canvas.get_color_mix()
                
                color_name = COLOR_NAMES.get(color, "Unknown")
                self.canvas.keyboard_command_status = f"OK: 0x{status:02X} -> {color_name} @ ({self.canvas.cursor_x},{self.canvas.cursor_y})"
                
            elif len(parts) == 3:
                # Three byte mode: X Y STATUS
                x = int(parts[0])
                y = int(parts[1])
                if parts[2].startswith('0x') or parts[2].startswith('0X'):
                    status = int(parts[2], 16)
                else:
                    status = int(parts[2])
                
                if not (0 <= x < self.canvas.grid_size):
                    self.canvas.keyboard_command_status = f"Error: X must be 0-{self.canvas.grid_size-1}"
                    return
                if not (0 <= y < self.canvas.grid_size):
                    self.canvas.keyboard_command_status = f"Error: Y must be 0-{self.canvas.grid_size-1}"
                    return
                if not (0 <= status <= 255):
                    self.canvas.keyboard_command_status = "Error: STATUS must be 0-255"
                    return
                
                # Send via I2C
                self.canvas.i2c_receive_byte(x)
                self.canvas.i2c_receive_byte(y)
                self.canvas.i2c_receive_byte(status)
                
                color = status & 0b111
                color_name = COLOR_NAMES.get(color, "Unknown")
                self.canvas.keyboard_command_status = f"OK: {color_name} at ({x}, {y})"
                
            else:
                self.canvas.keyboard_command_status = "Error: Use STATUS or X Y STATUS"
                return
            
            self.canvas.keyboard_input_buffer = ""
            
        except ValueError:
            self.canvas.keyboard_command_status = "Error: Invalid number format"
        except Exception as e:
            self.canvas.keyboard_command_status = f"Error: {str(e)}"
    
    def draw_header(self):
        """Draw header with title and controls hint."""
        title = self.font_title.render("TINY CANVAS - 256x256 Pixel Emulator", True, self.accent_color)
        title_rect = title.get_rect(center=(self.window_width // 2, 25))
        self.screen.blit(title, title_rect)
        
        if not self.canvas.keyboard_input_mode:
            hint = self.font_small.render("Arrow Keys: Move | R/G/B: Colors | I: Input Mode | Space: Brush/Eraser | C: Clear | ESC: Quit", True, (150, 150, 150))
        else:
            hint = self.font_small.render("INPUT MODE - Enter: Apply | ESC: Cancel", True, (255, 200, 100))
        hint_rect = hint.get_rect(center=(self.window_width // 2, 50))
        self.screen.blit(hint, hint_rect)
    
    def draw_grid(self):
        """Draw the 256x256 canvas grid."""
        for canvas_y in range(self.grid_size):
            for x in range(self.grid_size):
                screen_y = self.grid_size - 1 - canvas_y
                
                rect = pygame.Rect(
                    self.canvas_offset_x + x * self.cell_size,
                    self.canvas_offset_y + screen_y * self.cell_size,
                    self.cell_size,
                    self.cell_size
                )
                
                color_value = self.canvas.canvas[canvas_y][x]
                color = COLORS[color_value]
                pygame.draw.rect(self.screen, color, rect)
        
        # Draw border
        border_rect = pygame.Rect(
            self.canvas_offset_x - 2,
            self.canvas_offset_y - 2,
            self.canvas_width + 4,
            self.canvas_height + 4
        )
        pygame.draw.rect(self.screen, (100, 100, 100), border_rect, 2)
        
        # Draw cursor
        cursor_size = max(self.cell_size * 4, 8)
        cursor_screen_y = self.grid_size - 1 - self.canvas.cursor_y
        
        pixel_center_x = self.canvas_offset_x + self.canvas.cursor_x * self.cell_size + self.cell_size // 2
        pixel_center_y = self.canvas_offset_y + cursor_screen_y * self.cell_size + self.cell_size // 2
        
        cursor_rect = pygame.Rect(
            pixel_center_x - cursor_size // 2,
            pixel_center_y - cursor_size // 2,
            cursor_size,
            cursor_size
        )
        pygame.draw.rect(self.screen, (255, 255, 0), cursor_rect, 2)
    
    def draw_sidebar(self):
        """Draw the control panel sidebar."""
        sidebar_x = self.window_width - self.sidebar_width + 20
        y_offset = 70
        
        # Title
        title = self.font_large.render("Tiny Canvas", True, self.text_color)
        self.screen.blit(title, (sidebar_x, y_offset))
        y_offset += 40
        
        # Current color preview
        color_value = self.canvas.get_color_mix()
        color = COLORS[color_value]
        color_rect = pygame.Rect(sidebar_x, y_offset, 60, 60)
        pygame.draw.rect(self.screen, color, color_rect)
        pygame.draw.rect(self.screen, self.text_color, color_rect, 2)
        
        # Color name
        color_text = self.font_medium.render(COLOR_NAMES[color_value], True, self.text_color)
        self.screen.blit(color_text, (sidebar_x + 70, y_offset + 18))
        y_offset += 80
        
        # Mode
        mode = "BRUSH" if self.canvas.sw_brush else "ERASER"
        mode_color = (0, 255, 0) if self.canvas.sw_brush else (255, 100, 100)
        mode_text = self.font_medium.render(f"Mode: {mode}", True, mode_color)
        self.screen.blit(mode_text, (sidebar_x, y_offset))
        y_offset += 35
        
        # RGB switches
        self.draw_switch_indicator(sidebar_x, y_offset, "R", self.canvas.sw_red, (255, 0, 0))
        y_offset += 35
        self.draw_switch_indicator(sidebar_x, y_offset, "G", self.canvas.sw_green, (0, 255, 0))
        y_offset += 35
        self.draw_switch_indicator(sidebar_x, y_offset, "B", self.canvas.sw_blue, (0, 0, 255))
        y_offset += 45
        
        # Position
        pos_text = self.font_small.render(f"Position: ({self.canvas.cursor_x}, {self.canvas.cursor_y})", True, self.text_color)
        self.screen.blit(pos_text, (sidebar_x, y_offset))
        y_offset += 25
        
        # Status register
        status = self.canvas.get_status()
        status_text = self.font_small.render(f"Status: 0x{status:02X}", True, self.text_color)
        self.screen.blit(status_text, (sidebar_x, y_offset))
        y_offset += 30
        
        # I2C section
        i2c_header = self.font_small.render("I2C: Automatic", True, (100, 255, 100))
        self.screen.blit(i2c_header, (sidebar_x, y_offset))
        y_offset += 22
        
        i2c_info1 = self.font_small.render("State change -> I2C send", True, (180, 180, 180))
        self.screen.blit(i2c_info1, (sidebar_x, y_offset))
        y_offset += 20
        
        i2c_info2 = self.font_small.render("I2C receive -> Paint pixel", True, (180, 180, 180))
        self.screen.blit(i2c_info2, (sidebar_x, y_offset))
        y_offset += 25
        
        # External I2C indicator
        ext_text = self.font_small.render("External I2C: Ready", True, (150, 150, 150))
        self.screen.blit(ext_text, (sidebar_x, y_offset))
        y_offset += 20
        
        cmd_text = self.font_small.render(f"  Commands: {self.canvas.external_commands_received}", True, (180, 180, 180))
        self.screen.blit(cmd_text, (sidebar_x, y_offset))
        y_offset += 30
        
        # I2C Communication
        i2c_comm = self.font_small.render("I2C Communication:", True, (100, 200, 255))
        self.screen.blit(i2c_comm, (sidebar_x, y_offset))
        y_offset += 22
        
        buffer_text = self.font_small.render(f"Buffer: {len(self.canvas.i2c_buffer)}/3 bytes", True, self.text_color)
        self.screen.blit(buffer_text, (sidebar_x, y_offset))
        y_offset += 22
        
        # Last I2C transmission
        if self.canvas.i2c_status != 0 or self.canvas.i2c_x != 0 or self.canvas.i2c_y != 0:
            last_text = self.font_small.render("Last I2C Transmission:", True, self.text_color)
            self.screen.blit(last_text, (sidebar_x, y_offset))
            y_offset += 20
            
            byte1 = self.font_small.render(f"Byte 1 (X):  0x{self.canvas.i2c_x:02X} = {self.canvas.i2c_x}", True, (255, 200, 100))
            self.screen.blit(byte1, (sidebar_x, y_offset))
            y_offset += 20
            
            byte2 = self.font_small.render(f"Byte 2 (Y):  0x{self.canvas.i2c_y:02X} = {self.canvas.i2c_y}", True, (255, 200, 100))
            self.screen.blit(byte2, (sidebar_x, y_offset))
            y_offset += 20
            
            byte3 = self.font_small.render(f"Byte 3 (St): 0x{self.canvas.i2c_status:02X}", True, (255, 200, 100))
            self.screen.blit(byte3, (sidebar_x, y_offset))
            y_offset += 20
            
            # Status breakdown
            decode1 = self.font_small.render(f"  [7:4]={self.canvas.i2c_status >> 4:04b} [3]={(self.canvas.i2c_status >> 3) & 1}", True, (180, 180, 180))
            self.screen.blit(decode1, (sidebar_x, y_offset))
            y_offset += 18
            
            last_color = self.canvas.i2c_status & 0b111
            color_name = COLOR_NAMES.get(last_color, "Unknown")
            decode2 = self.font_small.render(f"  RGB[2:0]: {color_name} (0b{last_color:03b})", True, (180, 180, 180))
            self.screen.blit(decode2, (sidebar_x, y_offset))
    
    def draw_switch_indicator(self, x, y, label, state, color):
        """Draw a switch indicator (on/off)."""
        label_text = self.font_medium.render(label, True, self.text_color)
        self.screen.blit(label_text, (x, y))
        
        switch_x = x + 30
        switch_rect = pygame.Rect(switch_x, y, 50, 24)
        switch_color = color if state else (60, 60, 60)
        pygame.draw.rect(self.screen, switch_color, switch_rect)
        pygame.draw.rect(self.screen, self.text_color, switch_rect, 1)
        
        state_text = "ON" if state else "OFF"
        state_render = self.font_small.render(state_text, True, self.text_color)
        self.screen.blit(state_render, (switch_x + 90, y + 4))
    
    def draw_keyboard_input(self):
        """Draw the keyboard input box when in input mode."""
        if not self.canvas.keyboard_input_mode and not self.canvas.keyboard_command_status:
            return
        
        box_height = 80
        box_y = self.window_height - box_height - 10
        box_rect = pygame.Rect(10, box_y, self.window_width - 20, box_height)
        
        pygame.draw.rect(self.screen, (40, 40, 60), box_rect)
        border_color = (100, 200, 255) if self.canvas.keyboard_input_mode else (100, 100, 100)
        pygame.draw.rect(self.screen, border_color, box_rect, 2)
        
        y_offset = box_y + 10
        
        if self.canvas.keyboard_input_mode:
            title = self.font_medium.render("Input Mode - Enter command:", True, (100, 200, 255))
            self.screen.blit(title, (20, y_offset))
            y_offset += 28
            
            input_text = self.canvas.keyboard_input_buffer + "_"
            input_render = self.font_medium.render(input_text, True, (255, 255, 0))
            self.screen.blit(input_render, (20, y_offset))
        
        if self.canvas.keyboard_command_status:
            status_y = box_y + box_height - 25
            status_color = (100, 255, 100) if "OK" in self.canvas.keyboard_command_status else (255, 100, 100)
            status_render = self.font_small.render(self.canvas.keyboard_command_status, True, status_color)
            self.screen.blit(status_render, (20, status_y))
    
    def run(self):
        """Main emulator loop."""
        running = True
        
        print("=" * 60)
        print("Tiny Canvas Emulator Started")
        print("=" * 60)
        print("Canvas: 256x256 pixels")
        print("Coordinate System: (0,0) = BOTTOM-LEFT")
        print("")
        print("IMPORTANT: In brush mode with RGB=000, moving does NOT paint!")
        print("           Select at least one color to paint, or use eraser mode.")
        print("=" * 60)
        print("\nControls:")
        print("  Arrow Keys  = Move cursor")
        print("  R           = Toggle RED")
        print("  G           = Toggle GREEN")  
        print("  B           = Toggle BLUE")
        print("  SPACE       = Toggle BRUSH/ERASER")
        print("  I           = Keyboard Input Mode")
        print("  C           = Clear canvas")
        print("  ESC / Q     = Quit")
        print("=" * 60)
        
        while running:
            running = self.handle_events()
            
            current_time = pygame.time.get_ticks()
            self.canvas.update_cursor(current_time)
            self.canvas.auto_send_i2c_if_changed()
            
            self.screen.fill(self.bg_color)
            self.draw_header()
            self.draw_grid()
            self.draw_sidebar()
            self.draw_keyboard_input()
            
            pygame.display.flip()
            self.clock.tick(self.fps)
        
        pygame.quit()
        print("\nEmulator closed.")


def main():
    emulator = CanvasEmulator()
    emulator.run()


if __name__ == "__main__":
    main()

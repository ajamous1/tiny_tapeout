#!/usr/bin/env python3
"""
Tiny Canvas Emulator - Full Feature Version
Supports: Brush Size, Symmetry, Draw Modes, Undo/Redo (per stroke)
"""

import pygame
import sys
import os
import random

# ============================================================================
# Colour Definitions
# ============================================================================
COLORS = {
    0b000: (0, 0, 0),       # Black
    0b001: (0, 0, 255),     # Blue
    0b010: (0, 255, 0),     # Green
    0b011: (0, 255, 255),   # Cyan
    0b100: (255, 0, 0),     # Red
    0b101: (255, 0, 255),   # Magenta
    0b110: (255, 255, 0),   # Yellow
    0b111: (255, 255, 255), # White
}

COLOR_NAMES = {
    0b000: "Black", 0b001: "Blue", 0b010: "Green", 0b011: "Cyan",
    0b100: "Red", 0b101: "Magenta", 0b110: "Yellow", 0b111: "White"
}

DRAW_MODES = ["Freehand", "Line", "Rectangle", "Spray"]
SYMMETRY_MODES = ["Off", "H-Mirror", "V-Mirror", "4-Way"]


class TinyCanvas:
    """Emulates the Tiny Canvas hardware with all new features."""
    
    def __init__(self):
        self.grid_size = 256
        self.canvas = [[0 for _ in range(self.grid_size)] for _ in range(self.grid_size)]
        
        # Position
        self.cursor_x = 128
        self.cursor_y = 128
        
        # Color toggles
        self.sw_red = False
        self.sw_green = False
        self.sw_blue = False
        self.brush_mode = True
        
        # New features
        self.brush_size = 0      # 0-7 (1x1 to 8x8)
        self.symmetry_mode = 0   # 0=off, 1=H, 2=V, 3=4-way
        self.draw_mode = 0       # 0=freehand, 1=line, 2=rect, 3=spray
        
        # Line/Rect point storage
        self.point_a = None
        
        # Undo/Redo - stores STROKES not individual pixels
        # Each stroke is a list of (x, y, old_color, new_color)
        self.undo_buffer = []    # List of strokes
        self.redo_buffer = []    # List of strokes
        self.current_stroke = [] # Pixels being painted in current stroke
        self.max_undo = 32       # Max strokes to remember
        
        # I2C state
        self.i2c_x = 0
        self.i2c_y = 0
        self.i2c_status = 0
        self.i2c_count = 0
        
        # Timing
        self.last_move_time = 0
        self.move_delay = 50
    
    def get_color_mix(self):
        if self.brush_mode:
            return (int(self.sw_red) << 2) | (int(self.sw_green) << 1) | int(self.sw_blue)
        return 0
    
    def should_paint(self):
        if self.brush_mode:
            return self.sw_red or self.sw_green or self.sw_blue
        return True
    
    def get_status(self):
        status = 0
        status |= int(self.brush_mode) << 3
        status |= self.get_color_mix()
        return status
    
    def expand_brush(self, x, y):
        """Expand single pixel to brush size."""
        pixels = []
        half = self.brush_size // 2
        for dy in range(self.brush_size + 1):
            for dx in range(self.brush_size + 1):
                px = x + dx - half
                py = y + dy - half
                if 0 <= px < 256 and 0 <= py < 256:
                    pixels.append((px, py))
        return pixels
    
    def apply_symmetry(self, pixels):
        """Apply symmetry to pixel list."""
        result = list(pixels)
        if self.symmetry_mode == 1:  # H-mirror
            for x, y in pixels:
                mx = 255 - x
                if 0 <= mx < 256:
                    result.append((mx, y))
        elif self.symmetry_mode == 2:  # V-mirror
            for x, y in pixels:
                my = 255 - y
                if 0 <= my < 256:
                    result.append((x, my))
        elif self.symmetry_mode == 3:  # 4-way
            for x, y in pixels:
                mx, my = 255 - x, 255 - y
                if 0 <= mx < 256:
                    result.append((mx, y))
                if 0 <= my < 256:
                    result.append((x, my))
                if 0 <= mx < 256 and 0 <= my < 256:
                    result.append((mx, my))
        return list(set(result))
    
    def paint_pixels(self, pixels, color, track_stroke=True):
        """Paint multiple pixels, tracking for undo."""
        for x, y in pixels:
            if 0 <= x < 256 and 0 <= y < 256:
                old_color = self.canvas[y][x]
                if old_color != color:
                    if track_stroke:
                        self.current_stroke.append((x, y, old_color, color))
                    self.canvas[y][x] = color
        self.i2c_count += len(pixels)
    
    def start_stroke(self):
        """Begin a new stroke for undo tracking."""
        self.current_stroke = []
    
    def end_stroke(self):
        """End current stroke and save to undo buffer."""
        if self.current_stroke:
            self.undo_buffer.append(self.current_stroke)
            if len(self.undo_buffer) > self.max_undo:
                self.undo_buffer.pop(0)
            self.redo_buffer.clear()
        self.current_stroke = []
    
    def paint_at(self, x, y):
        """Paint at position with brush size and symmetry."""
        if not self.should_paint():
            return
        color = self.get_color_mix()
        pixels = self.expand_brush(x, y)
        pixels = self.apply_symmetry(pixels)
        self.paint_pixels(pixels, color)
        self.i2c_x = x
        self.i2c_y = y
        self.i2c_status = self.get_status()
    
    def draw_line(self, x0, y0, x1, y1):
        """Draw line from (x0,y0) to (x1,y1)."""
        self.start_stroke()
        color = self.get_color_mix()
        pixels = []
        
        x, y = x0, y0
        while True:
            expanded = self.expand_brush(x, y)
            pixels.extend(expanded)
            
            if x == x1 and y == y1:
                break
            
            if x < x1: x += 1
            elif x > x1: x -= 1
            
            if y < y1: y += 1
            elif y > y1: y -= 1
        
        pixels = self.apply_symmetry(pixels)
        self.paint_pixels(list(set(pixels)), color)
        self.end_stroke()
    
    def draw_rect(self, x0, y0, x1, y1):
        """Draw rectangle outline."""
        self.start_stroke()
        color = self.get_color_mix()
        pixels = []
        
        min_x, max_x = min(x0, x1), max(x0, x1)
        min_y, max_y = min(y0, y1), max(y0, y1)
        
        for x in range(min_x, max_x + 1):
            pixels.extend(self.expand_brush(x, max_y))
            pixels.extend(self.expand_brush(x, min_y))
        
        for y in range(min_y + 1, max_y):
            pixels.extend(self.expand_brush(min_x, y))
            pixels.extend(self.expand_brush(max_x, y))
        
        pixels = self.apply_symmetry(list(set(pixels)))
        self.paint_pixels(pixels, color)
        self.end_stroke()
    
    def spray_paint(self, x, y):
        """Spray random pixels around position."""
        color = self.get_color_mix()
        pixels = []
        for _ in range(8):
            dx = random.randint(-8, 7)
            dy = random.randint(-8, 7)
            px, py = x + dx, y + dy
            if 0 <= px < 256 and 0 <= py < 256:
                pixels.append((px, py))
        pixels = self.apply_symmetry(pixels)
        self.paint_pixels(pixels, color)
    
    def undo(self):
        """Undo last stroke (entire brush action)."""
        if self.undo_buffer:
            stroke = self.undo_buffer.pop()
            # Restore all pixels in this stroke
            for x, y, old_color, new_color in stroke:
                self.canvas[y][x] = old_color
            self.redo_buffer.append(stroke)
            return len(stroke)  # Return pixel count
        return 0
    
    def redo(self):
        """Redo last undone stroke."""
        if self.redo_buffer:
            stroke = self.redo_buffer.pop()
            # Re-apply all pixels in this stroke
            for x, y, old_color, new_color in stroke:
                self.canvas[y][x] = new_color
            self.undo_buffer.append(stroke)
            return len(stroke)
        return 0
    
    def set_point(self):
        """Set point A or B for line/rect mode."""
        if self.draw_mode in [1, 2]:
            if self.point_a is None:
                self.point_a = (self.cursor_x, self.cursor_y)
                return "Point A set"
            else:
                x0, y0 = self.point_a
                x1, y1 = self.cursor_x, self.cursor_y
                self.point_a = None
                if self.draw_mode == 1:
                    self.draw_line(x0, y0, x1, y1)
                    return "Line drawn"
                else:
                    self.draw_rect(x0, y0, x1, y1)
                    return "Rectangle drawn"
        return None
    
    def update_cursor(self, current_time, direction):
        """Update cursor based on direction."""
        if current_time - self.last_move_time < self.move_delay:
            return False
        
        moved = False
        if direction == 'up' and self.cursor_y < 255:
            self.cursor_y += 1
            moved = True
        elif direction == 'down' and self.cursor_y > 0:
            self.cursor_y -= 1
            moved = True
        elif direction == 'left' and self.cursor_x > 0:
            self.cursor_x -= 1
            moved = True
        elif direction == 'right' and self.cursor_x < 255:
            self.cursor_x += 1
            moved = True
        
        if moved:
            self.last_move_time = current_time
            if self.draw_mode == 0 and self.should_paint():
                self.paint_at(self.cursor_x, self.cursor_y)
            elif self.draw_mode == 3 and self.should_paint():
                self.spray_paint(self.cursor_x, self.cursor_y)
        
        return moved
    
    def clear(self):
        self.canvas = [[0 for _ in range(self.grid_size)] for _ in range(self.grid_size)]
        self.undo_buffer.clear()
        self.redo_buffer.clear()
        self.current_stroke = []
        self.point_a = None


class CanvasEmulator:
    """Pygame GUI for Tiny Canvas."""
    
    def __init__(self):
        pygame.init()
        
        info = pygame.display.Info()
        self.window_width = int(info.current_w * 0.85)
        self.window_height = int(info.current_h * 0.85)
        
        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
        pygame.display.set_caption("Tiny Canvas - Full Features")
        
        self.grid_size = 256
        self.sidebar_width = 380
        
        self.recalculate_layout()
        
        # Colors
        self.bg_color = (25, 28, 38)
        self.panel_color = (35, 40, 52)
        self.text_color = (220, 220, 230)
        self.accent_color = (80, 200, 255)
        self.highlight = (255, 200, 80)
        
        # Fonts
        self.font_title = pygame.font.Font(None, 36)
        self.font_large = pygame.font.Font(None, 28)
        self.font_medium = pygame.font.Font(None, 22)
        self.font_small = pygame.font.Font(None, 18)
        
        self.canvas = TinyCanvas()
        self.clock = pygame.time.Clock()
        self.message = ""
        self.message_time = 0
        
        # Track if currently in a freehand stroke
        self.in_stroke = False
    
    def recalculate_layout(self):
        available_w = self.window_width - self.sidebar_width - 60
        available_h = self.window_height - 100
        self.cell_size = min(available_w // self.grid_size, available_h // self.grid_size)
        self.cell_size = max(self.cell_size, 2)
        self.canvas_width = self.cell_size * self.grid_size
        self.canvas_height = self.cell_size * self.grid_size
        self.canvas_x = (self.window_width - self.sidebar_width - self.canvas_width) // 2
        self.canvas_y = (self.window_height - self.canvas_height) // 2 + 30
    
    def show_message(self, msg):
        self.message = msg
        self.message_time = pygame.time.get_ticks()
    
    def handle_events(self):
        current_time = pygame.time.get_ticks()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            if event.type == pygame.VIDEORESIZE:
                self.window_width, self.window_height = event.w, event.h
                self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                self.recalculate_layout()
            
            if event.type == pygame.KEYDOWN:
                # Color toggles
                if event.key == pygame.K_r:
                    self.canvas.sw_red = not self.canvas.sw_red
                    self.show_message(f"Red {'ON' if self.canvas.sw_red else 'OFF'}")
                elif event.key == pygame.K_g:
                    self.canvas.sw_green = not self.canvas.sw_green
                    self.show_message(f"Green {'ON' if self.canvas.sw_green else 'OFF'}")
                elif event.key == pygame.K_b:
                    self.canvas.sw_blue = not self.canvas.sw_blue
                    self.show_message(f"Blue {'ON' if self.canvas.sw_blue else 'OFF'}")
                
                # Brush/Eraser or Set Point
                elif event.key == pygame.K_SPACE:
                    if self.canvas.draw_mode in [1, 2]:
                        result = self.canvas.set_point()
                        if result:
                            self.show_message(result)
                    else:
                        self.canvas.brush_mode = not self.canvas.brush_mode
                        self.show_message(f"Mode: {'Brush' if self.canvas.brush_mode else 'Eraser'}")
                
                # Brush size
                elif event.key == pygame.K_MINUS or event.key == pygame.K_KP_MINUS:
                    if self.canvas.brush_size > 0:
                        self.canvas.brush_size -= 1
                        self.show_message(f"Brush: {self.canvas.brush_size + 1}x{self.canvas.brush_size + 1}")
                elif event.key == pygame.K_EQUALS or event.key == pygame.K_KP_PLUS:
                    if self.canvas.brush_size < 7:
                        self.canvas.brush_size += 1
                        self.show_message(f"Brush: {self.canvas.brush_size + 1}x{self.canvas.brush_size + 1}")
                
                # Draw mode
                elif event.key == pygame.K_TAB:
                    self.canvas.draw_mode = (self.canvas.draw_mode + 1) % 4
                    self.canvas.point_a = None
                    self.show_message(f"Mode: {DRAW_MODES[self.canvas.draw_mode]}")
                
                # Symmetry
                elif event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_SHIFT:
                    self.canvas.symmetry_mode = (self.canvas.symmetry_mode + 1) % 4
                    self.show_message(f"Symmetry: {SYMMETRY_MODES[self.canvas.symmetry_mode]}")
                
                # Undo
                elif event.key == pygame.K_z or event.key == pygame.K_u:
                    count = self.canvas.undo()
                    if count:
                        self.show_message(f"Undo ({count} pixels)")
                    else:
                        self.show_message("Nothing to undo")
                
                # Redo
                elif event.key == pygame.K_y:
                    count = self.canvas.redo()
                    if count:
                        self.show_message(f"Redo ({count} pixels)")
                    else:
                        self.show_message("Nothing to redo")
                
                # Clear
                elif event.key == pygame.K_c:
                    self.canvas.clear()
                    self.show_message("Canvas cleared")
                
                # Quit
                elif event.key in (pygame.K_ESCAPE, pygame.K_q):
                    return False
        
        # Movement (held keys) - track as single stroke
        keys = pygame.key.get_pressed()
        any_movement = keys[pygame.K_UP] or keys[pygame.K_DOWN] or keys[pygame.K_LEFT] or keys[pygame.K_RIGHT]
        
        # Start stroke when beginning to move in freehand/spray mode
        if any_movement and not self.in_stroke:
            if self.canvas.draw_mode in [0, 3]:  # Freehand or Spray
                self.canvas.start_stroke()
                self.in_stroke = True
        
        # End stroke when stopping movement
        if not any_movement and self.in_stroke:
            self.canvas.end_stroke()
            self.in_stroke = False
        
        if keys[pygame.K_UP]:
            self.canvas.update_cursor(current_time, 'up')
        elif keys[pygame.K_DOWN]:
            self.canvas.update_cursor(current_time, 'down')
        elif keys[pygame.K_LEFT]:
            self.canvas.update_cursor(current_time, 'left')
        elif keys[pygame.K_RIGHT]:
            self.canvas.update_cursor(current_time, 'right')
        
        return True
    
    def draw_header(self):
        title = self.font_title.render("TINY CANVAS - Full Feature Emulator", True, self.accent_color)
        self.screen.blit(title, (self.window_width // 2 - title.get_width() // 2, 15))
        
        hint = "Arrows:Move | R/G/B:Color | Space:Brush/Point | Tab:Mode | Shift+S:Symmetry | +/-:Size | Z:Undo | Y:Redo"
        hint_surf = self.font_small.render(hint, True, (120, 120, 130))
        self.screen.blit(hint_surf, (self.window_width // 2 - hint_surf.get_width() // 2, 45))
    
    def draw_canvas(self):
        for cy in range(self.grid_size):
            for cx in range(self.grid_size):
                screen_y = self.grid_size - 1 - cy
                rect = pygame.Rect(
                    self.canvas_x + cx * self.cell_size,
                    self.canvas_y + screen_y * self.cell_size,
                    self.cell_size, self.cell_size
                )
                color = COLORS[self.canvas.canvas[cy][cx]]
                pygame.draw.rect(self.screen, color, rect)
        
        pygame.draw.rect(self.screen, (80, 80, 90),
                        (self.canvas_x - 2, self.canvas_y - 2,
                         self.canvas_width + 4, self.canvas_height + 4), 2)
        
        # Cursor (size reflects brush)
        cursor_size = max(self.cell_size * (self.canvas.brush_size + 2), 8)
        screen_y = self.grid_size - 1 - self.canvas.cursor_y
        cx = self.canvas_x + self.canvas.cursor_x * self.cell_size + self.cell_size // 2
        cy = self.canvas_y + screen_y * self.cell_size + self.cell_size // 2
        pygame.draw.rect(self.screen, (255, 255, 0),
                        (cx - cursor_size // 2, cy - cursor_size // 2, cursor_size, cursor_size), 2)
        
        # Point A marker
        if self.canvas.point_a:
            ax, ay = self.canvas.point_a
            screen_ay = self.grid_size - 1 - ay
            px = self.canvas_x + ax * self.cell_size + self.cell_size // 2
            py = self.canvas_y + screen_ay * self.cell_size + self.cell_size // 2
            pygame.draw.circle(self.screen, (255, 100, 100), (px, py), 6, 2)
    
    def draw_sidebar(self):
        sx = self.window_width - self.sidebar_width + 15
        y = 70
        
        pygame.draw.rect(self.screen, self.panel_color,
                        (sx - 10, y - 10, self.sidebar_width - 20, self.window_height - 90),
                        border_radius=10)
        
        # Color preview
        color = self.canvas.get_color_mix()
        pygame.draw.rect(self.screen, COLORS[color], (sx, y, 60, 60))
        pygame.draw.rect(self.screen, self.text_color, (sx, y, 60, 60), 2)
        
        name = self.font_large.render(COLOR_NAMES[color], True, self.text_color)
        self.screen.blit(name, (sx + 70, y + 5))
        
        mode_text = "BRUSH" if self.canvas.brush_mode else "ERASER"
        mode_color = (80, 255, 120) if self.canvas.brush_mode else (255, 100, 100)
        mode = self.font_medium.render(f"Mode: {mode_text}", True, mode_color)
        self.screen.blit(mode, (sx + 70, y + 35))
        y += 75
        
        # RGB switches
        for label, state, clr in [("R", self.canvas.sw_red, (255, 60, 60)),
                                   ("G", self.canvas.sw_green, (60, 255, 60)),
                                   ("B", self.canvas.sw_blue, (60, 60, 255))]:
            lbl = self.font_large.render(label, True, self.text_color)
            self.screen.blit(lbl, (sx, y))
            box_color = clr if state else (50, 50, 55)
            pygame.draw.rect(self.screen, box_color, (sx + 25, y, 50, 22))
            pygame.draw.rect(self.screen, self.text_color, (sx + 25, y, 50, 22), 1)
            st = self.font_small.render("ON" if state else "OFF", True, self.text_color)
            self.screen.blit(st, (sx + 85, y + 3))
            y += 28
        y += 10
        
        # Position
        pos = self.font_medium.render(f"Position: ({self.canvas.cursor_x}, {self.canvas.cursor_y})", True, self.text_color)
        self.screen.blit(pos, (sx, y))
        y += 25
        
        # Draw mode
        dm = self.font_medium.render(f"Draw Mode: {DRAW_MODES[self.canvas.draw_mode]}", True, self.highlight)
        self.screen.blit(dm, (sx, y))
        y += 25
        
        # Brush size
        bs = self.font_medium.render(f"Brush Size: {self.canvas.brush_size + 1}x{self.canvas.brush_size + 1}", True, self.text_color)
        self.screen.blit(bs, (sx, y))
        y += 25
        
        # Symmetry
        sym = self.font_medium.render(f"Symmetry: {SYMMETRY_MODES[self.canvas.symmetry_mode]}", True, self.text_color)
        self.screen.blit(sym, (sx, y))
        y += 25
        
        # Point A status
        if self.canvas.draw_mode in [1, 2]:
            if self.canvas.point_a:
                pa = self.font_small.render(f"Point A: {self.canvas.point_a}", True, (255, 150, 150))
            else:
                pa = self.font_small.render("Point A: Not set (Space)", True, (150, 150, 150))
            self.screen.blit(pa, (sx, y))
            y += 22
        
        y += 8
        
        # Undo/Redo - now shows strokes
        undo_count = len(self.canvas.undo_buffer)
        redo_count = len(self.canvas.redo_buffer)
        undo_text = f"Undo: {undo_count} strokes | Redo: {redo_count} strokes"
        undo = self.font_small.render(undo_text, True, (150, 150, 160))
        self.screen.blit(undo, (sx, y))
        y += 25
        
        # I2C stats
        i2c_header = self.font_medium.render("I2C Output:", True, self.accent_color)
        self.screen.blit(i2c_header, (sx, y))
        y += 22
        
        i2c_info = [
            f"X: 0x{self.canvas.i2c_x:02X} ({self.canvas.i2c_x})",
            f"Y: 0x{self.canvas.i2c_y:02X} ({self.canvas.i2c_y})",
            f"Status: 0x{self.canvas.i2c_status:02X}",
            f"Packets: {self.canvas.i2c_count}"
        ]
        for info in i2c_info:
            txt = self.font_small.render(info, True, (180, 180, 190))
            self.screen.blit(txt, (sx + 10, y))
            y += 18
        
        y += 15
        
        # Controls
        controls = self.font_medium.render("Controls:", True, self.text_color)
        self.screen.blit(controls, (sx, y))
        y += 22
        
        ctrl_list = [
            "Arrows = Move cursor",
            "R/G/B = Toggle colors",
            "Space = Brush/Eraser or Set Point",
            "Tab = Cycle draw mode",
            "Shift+S = Cycle symmetry",
            "+/- = Brush size",
            "Z = Undo stroke, Y = Redo stroke",
            "C = Clear canvas"
        ]
        for ctrl in ctrl_list:
            txt = self.font_small.render(ctrl, True, (140, 140, 150))
            self.screen.blit(txt, (sx, y))
            y += 17
    
    def draw_message(self):
        if self.message and pygame.time.get_ticks() - self.message_time < 2000:
            msg = self.font_large.render(self.message, True, self.highlight)
            pygame.draw.rect(self.screen, (40, 40, 50),
                           (self.canvas_x, self.canvas_y + self.canvas_height + 10,
                            msg.get_width() + 20, 30), border_radius=5)
            self.screen.blit(msg, (self.canvas_x + 10, self.canvas_y + self.canvas_height + 15))
    
    def run(self):
        print("=" * 60)
        print("Tiny Canvas - Full Feature Emulator")
        print("=" * 60)
        print("Features:")
        print("  - Brush Size: +/- keys (1x1 to 8x8)")
        print("  - Symmetry: Shift+S (Off, H-Mirror, V-Mirror, 4-Way)")
        print("  - Draw Modes: Tab (Freehand, Line, Rectangle, Spray)")
        print("  - Undo/Redo: Z and Y (undoes entire strokes, not pixels)")
        print("=" * 60)
        
        running = True
        while running:
            running = self.handle_events()
            
            self.screen.fill(self.bg_color)
            self.draw_header()
            self.draw_canvas()
            self.draw_sidebar()
            self.draw_message()
            
            pygame.display.flip()
            self.clock.tick(60)
        
        pygame.quit()


def main():
    emulator = CanvasEmulator()
    emulator.run()


if __name__ == "__main__":
    main()

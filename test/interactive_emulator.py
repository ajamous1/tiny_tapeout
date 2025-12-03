#!/usr/bin/env python3
"""
Tiny Canvas Emulator
Supports: Brush Size, Symmetry, Fill Rectangle, Undo/Redo
"""

import pygame
import sys
import os

COLORS = {
    0b000: (0, 0, 0), 0b001: (0, 0, 255), 0b010: (0, 255, 0), 0b011: (0, 255, 255),
    0b100: (255, 0, 0), 0b101: (255, 0, 255), 0b110: (255, 255, 0), 0b111: (255, 255, 255),
}
COLOR_NAMES = {
    0b000: "Black", 0b001: "Blue", 0b010: "Green", 0b011: "Cyan",
    0b100: "Red", 0b101: "Magenta", 0b110: "Yellow", 0b111: "White"
}
SYMMETRY_MODES = ["Off", "H-Mirror", "V-Mirror", "4-Way"]


class TinyCanvas:
    def __init__(self):
        self.grid_size = 256
        self.canvas = [[0 for _ in range(self.grid_size)] for _ in range(self.grid_size)]
        
        self.cursor_x = 128
        self.cursor_y = 128
        
        self.sw_red = False
        self.sw_green = False
        self.sw_blue = False
        self.brush_mode = True
        
        self.brush_size = 0
        self.symmetry_mode = 0
        self.fill_mode = False
        self.fill_corner_a = None
        
        self.undo_buffer = []
        self.redo_buffer = []
        self.current_stroke = []
        self.max_undo = 32
        
        self.i2c_x = 0
        self.i2c_y = 0
        self.i2c_status = 0
        self.i2c_count = 0
        
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
        return (int(self.brush_mode) << 3) | self.get_color_mix()
    
    def expand_brush(self, x, y):
        pixels = []
        half = self.brush_size // 2
        for dy in range(self.brush_size + 1):
            for dx in range(self.brush_size + 1):
                px, py = x + dx - half, y + dy - half
                if 0 <= px < 256 and 0 <= py < 256:
                    pixels.append((px, py))
        return pixels
    
    def apply_symmetry(self, pixels):
        result = list(pixels)
        if self.symmetry_mode == 1:
            for x, y in pixels:
                if 0 <= 255 - x < 256:
                    result.append((255 - x, y))
        elif self.symmetry_mode == 2:
            for x, y in pixels:
                if 0 <= 255 - y < 256:
                    result.append((x, 255 - y))
        elif self.symmetry_mode == 3:
            for x, y in pixels:
                result.append((255 - x, y))
                result.append((x, 255 - y))
                result.append((255 - x, 255 - y))
        return list(set(result))
    
    def paint_pixels(self, pixels, color):
        for x, y in pixels:
            if 0 <= x < 256 and 0 <= y < 256:
                old_color = self.canvas[y][x]
                if old_color != color:
                    self.current_stroke.append((x, y, old_color, color))
                    self.canvas[y][x] = color
        self.i2c_count += len(pixels)
    
    def start_stroke(self):
        self.current_stroke = []
    
    def end_stroke(self):
        if self.current_stroke:
            self.undo_buffer.append(self.current_stroke)
            if len(self.undo_buffer) > self.max_undo:
                self.undo_buffer.pop(0)
            self.redo_buffer.clear()
        self.current_stroke = []
    
    def paint_at(self, x, y):
        if not self.should_paint():
            return
        color = self.get_color_mix()
        pixels = self.expand_brush(x, y)
        pixels = self.apply_symmetry(pixels)
        self.paint_pixels(pixels, color)
        self.i2c_x = x
        self.i2c_y = y
        self.i2c_status = self.get_status()
    
    def fill_rect(self, x0, y0, x1, y1):
        """Fill a rectangular region."""
        self.start_stroke()
        color = self.get_color_mix()
        
        min_x, max_x = min(x0, x1), max(x0, x1)
        min_y, max_y = min(y0, y1), max(y0, y1)
        
        pixels = []
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                expanded = self.expand_brush(x, y)
                pixels.extend(expanded)
        
        pixels = self.apply_symmetry(list(set(pixels)))
        self.paint_pixels(pixels, color)
        self.end_stroke()
        
        self.i2c_x = x1
        self.i2c_y = y1
        self.i2c_status = self.get_status()
        return (max_x - min_x + 1) * (max_y - min_y + 1)
    
    def set_fill_corner(self):
        """Set corner for fill rectangle."""
        if self.fill_corner_a is None:
            self.fill_corner_a = (self.cursor_x, self.cursor_y)
            return "Corner A set"
        else:
            x0, y0 = self.fill_corner_a
            x1, y1 = self.cursor_x, self.cursor_y
            self.fill_corner_a = None
            count = self.fill_rect(x0, y0, x1, y1)
            return f"Filled {count} pixels"
    
    def undo(self):
        if self.undo_buffer:
            stroke = self.undo_buffer.pop()
            for x, y, old_color, new_color in stroke:
                self.canvas[y][x] = old_color
            self.redo_buffer.append(stroke)
            return len(stroke)
        return 0
    
    def redo(self):
        if self.redo_buffer:
            stroke = self.redo_buffer.pop()
            for x, y, old_color, new_color in stroke:
                self.canvas[y][x] = new_color
            self.undo_buffer.append(stroke)
            return len(stroke)
        return 0
    
    def update_cursor(self, current_time, direction):
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
            # Only paint in freehand mode (not fill mode)
            if not self.fill_mode and self.should_paint():
                self.paint_at(self.cursor_x, self.cursor_y)
        
        return moved
    
    def clear(self):
        self.canvas = [[0 for _ in range(self.grid_size)] for _ in range(self.grid_size)]
        self.undo_buffer.clear()
        self.redo_buffer.clear()
        self.current_stroke = []
        self.fill_corner_a = None


class CanvasEmulator:
    def __init__(self):
        pygame.init()
        
        info = pygame.display.Info()
        self.window_width = int(info.current_w * 0.85)
        self.window_height = int(info.current_h * 0.85)
        
        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
        pygame.display.set_caption("Tiny Canvas Emulator")
        
        self.grid_size = 256
        self.sidebar_width = 380
        self.recalculate_layout()
        
        self.bg_color = (25, 28, 38)
        self.panel_color = (35, 40, 52)
        self.text_color = (220, 220, 230)
        self.accent_color = (80, 200, 255)
        self.highlight = (255, 200, 80)
        
        self.font_title = pygame.font.Font(None, 36)
        self.font_large = pygame.font.Font(None, 28)
        self.font_medium = pygame.font.Font(None, 22)
        self.font_small = pygame.font.Font(None, 18)
        
        self.canvas = TinyCanvas()
        self.clock = pygame.time.Clock()
        self.message = ""
        self.message_time = 0
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
                if event.key == pygame.K_r:
                    self.canvas.sw_red = not self.canvas.sw_red
                    self.show_message(f"Red {'ON' if self.canvas.sw_red else 'OFF'}")
                elif event.key == pygame.K_g:
                    self.canvas.sw_green = not self.canvas.sw_green
                    self.show_message(f"Green {'ON' if self.canvas.sw_green else 'OFF'}")
                elif event.key == pygame.K_b:
                    self.canvas.sw_blue = not self.canvas.sw_blue
                    self.show_message(f"Blue {'ON' if self.canvas.sw_blue else 'OFF'}")
                
                elif event.key == pygame.K_SPACE:
                    if self.canvas.fill_mode:
                        # Set fill corner
                        result = self.canvas.set_fill_corner()
                        self.show_message(result)
                    else:
                        # Toggle brush/eraser
                        self.canvas.brush_mode = not self.canvas.brush_mode
                        self.show_message(f"Mode: {'Brush' if self.canvas.brush_mode else 'Eraser'}")
                
                elif event.key == pygame.K_TAB:
                    # Toggle fill mode
                    self.canvas.fill_mode = not self.canvas.fill_mode
                    self.canvas.fill_corner_a = None
                    self.show_message(f"Fill Mode: {'ON' if self.canvas.fill_mode else 'OFF'}")
                
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    if self.canvas.brush_size > 0:
                        self.canvas.brush_size -= 1
                        self.show_message(f"Brush: {self.canvas.brush_size + 1}x{self.canvas.brush_size + 1}")
                elif event.key in (pygame.K_EQUALS, pygame.K_KP_PLUS):
                    if self.canvas.brush_size < 7:
                        self.canvas.brush_size += 1
                        self.show_message(f"Brush: {self.canvas.brush_size + 1}x{self.canvas.brush_size + 1}")
                
                elif event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_SHIFT:
                    self.canvas.symmetry_mode = (self.canvas.symmetry_mode + 1) % 4
                    self.show_message(f"Symmetry: {SYMMETRY_MODES[self.canvas.symmetry_mode]}")
                
                elif event.key in (pygame.K_z, pygame.K_u):
                    count = self.canvas.undo()
                    self.show_message(f"Undo ({count} pixels)" if count else "Nothing to undo")
                elif event.key == pygame.K_y:
                    count = self.canvas.redo()
                    self.show_message(f"Redo ({count} pixels)" if count else "Nothing to redo")
                
                elif event.key == pygame.K_c:
                    self.canvas.clear()
                    self.show_message("Canvas cleared")
                
                elif event.key in (pygame.K_ESCAPE, pygame.K_q):
                    return False
        
        keys = pygame.key.get_pressed()
        any_movement = keys[pygame.K_UP] or keys[pygame.K_DOWN] or keys[pygame.K_LEFT] or keys[pygame.K_RIGHT]
        
        # Stroke tracking only in freehand mode
        if not self.canvas.fill_mode:
            if any_movement and not self.in_stroke:
                self.canvas.start_stroke()
                self.in_stroke = True
            
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
        title = self.font_title.render("TINY CANVAS EMULATOR", True, self.accent_color)
        self.screen.blit(title, (self.window_width // 2 - title.get_width() // 2, 15))
        
        hint = "Arrows:Move | R/G/B:Color | Space:Brush/Fill | Tab:Fill Mode | Shift+S:Sym | +/-:Size | Z:Undo"
        self.screen.blit(self.font_small.render(hint, True, (120, 120, 130)),
                        (self.window_width // 2 - 300, 45))
    
    def draw_canvas(self):
        for cy in range(self.grid_size):
            for cx in range(self.grid_size):
                screen_y = self.grid_size - 1 - cy
                rect = pygame.Rect(self.canvas_x + cx * self.cell_size,
                                  self.canvas_y + screen_y * self.cell_size,
                                  self.cell_size, self.cell_size)
                pygame.draw.rect(self.screen, COLORS[self.canvas.canvas[cy][cx]], rect)
        
        pygame.draw.rect(self.screen, (80, 80, 90),
                        (self.canvas_x - 2, self.canvas_y - 2,
                         self.canvas_width + 4, self.canvas_height + 4), 2)
        
        # Cursor
        cursor_size = max(self.cell_size * (self.canvas.brush_size + 2), 8)
        screen_y = self.grid_size - 1 - self.canvas.cursor_y
        cx = self.canvas_x + self.canvas.cursor_x * self.cell_size + self.cell_size // 2
        cy = self.canvas_y + screen_y * self.cell_size + self.cell_size // 2
        cursor_color = (255, 100, 100) if self.canvas.fill_mode else (255, 255, 0)
        pygame.draw.rect(self.screen, cursor_color,
                        (cx - cursor_size // 2, cy - cursor_size // 2, cursor_size, cursor_size), 2)
        
        # Fill corner A marker
        if self.canvas.fill_corner_a:
            ax, ay = self.canvas.fill_corner_a
            screen_ay = self.grid_size - 1 - ay
            px = self.canvas_x + ax * self.cell_size + self.cell_size // 2
            py = self.canvas_y + screen_ay * self.cell_size + self.cell_size // 2
            pygame.draw.circle(self.screen, (255, 100, 100), (px, py), 8, 2)
            
            # Preview rectangle
            bx, by = self.canvas.cursor_x, self.canvas.cursor_y
            min_x, max_x = min(ax, bx), max(ax, bx)
            min_y, max_y = min(ay, by), max(ay, by)
            
            rx = self.canvas_x + min_x * self.cell_size
            ry = self.canvas_y + (self.grid_size - 1 - max_y) * self.cell_size
            rw = (max_x - min_x + 1) * self.cell_size
            rh = (max_y - min_y + 1) * self.cell_size
            pygame.draw.rect(self.screen, (255, 100, 100, 128), (rx, ry, rw, rh), 1)
    
    def draw_sidebar(self):
        sx = self.window_width - self.sidebar_width + 15
        y = 70
        
        pygame.draw.rect(self.screen, self.panel_color,
                        (sx - 10, y - 10, self.sidebar_width - 20, self.window_height - 90),
                        border_radius=10)
        
        color = self.canvas.get_color_mix()
        pygame.draw.rect(self.screen, COLORS[color], (sx, y, 60, 60))
        pygame.draw.rect(self.screen, self.text_color, (sx, y, 60, 60), 2)
        
        self.screen.blit(self.font_large.render(COLOR_NAMES[color], True, self.text_color), (sx + 70, y + 5))
        
        mode_text = "BRUSH" if self.canvas.brush_mode else "ERASER"
        mode_color = (80, 255, 120) if self.canvas.brush_mode else (255, 100, 100)
        self.screen.blit(self.font_medium.render(f"Paint: {mode_text}", True, mode_color), (sx + 70, y + 35))
        y += 75
        
        # Fill mode indicator
        fill_text = "FILL MODE ON" if self.canvas.fill_mode else "Fill Mode Off"
        fill_color = (255, 100, 100) if self.canvas.fill_mode else (100, 100, 110)
        self.screen.blit(self.font_medium.render(fill_text, True, fill_color), (sx, y))
        y += 25
        
        if self.canvas.fill_mode and self.canvas.fill_corner_a:
            corner_text = f"Corner A: {self.canvas.fill_corner_a}"
            self.screen.blit(self.font_small.render(corner_text, True, (255, 150, 150)), (sx, y))
            y += 20
        y += 5
        
        for label, state, clr in [("R", self.canvas.sw_red, (255, 60, 60)),
                                   ("G", self.canvas.sw_green, (60, 255, 60)),
                                   ("B", self.canvas.sw_blue, (60, 60, 255))]:
            self.screen.blit(self.font_large.render(label, True, self.text_color), (sx, y))
            pygame.draw.rect(self.screen, clr if state else (50, 50, 55), (sx + 25, y, 50, 22))
            pygame.draw.rect(self.screen, self.text_color, (sx + 25, y, 50, 22), 1)
            self.screen.blit(self.font_small.render("ON" if state else "OFF", True, self.text_color), (sx + 85, y + 3))
            y += 28
        y += 10
        
        self.screen.blit(self.font_medium.render(f"Position: ({self.canvas.cursor_x}, {self.canvas.cursor_y})", True, self.text_color), (sx, y))
        y += 25
        self.screen.blit(self.font_medium.render(f"Brush: {self.canvas.brush_size + 1}x{self.canvas.brush_size + 1}", True, self.text_color), (sx, y))
        y += 25
        self.screen.blit(self.font_medium.render(f"Symmetry: {SYMMETRY_MODES[self.canvas.symmetry_mode]}", True, self.text_color), (sx, y))
        y += 30
        
        self.screen.blit(self.font_small.render(f"Undo: {len(self.canvas.undo_buffer)} | Redo: {len(self.canvas.redo_buffer)}", True, (150, 150, 160)), (sx, y))
        y += 25
        
        self.screen.blit(self.font_medium.render("I2C Output:", True, self.accent_color), (sx, y))
        y += 22
        for info in [f"X: 0x{self.canvas.i2c_x:02X}", f"Y: 0x{self.canvas.i2c_y:02X}",
                     f"Status: 0x{self.canvas.i2c_status:02X}", f"Packets: {self.canvas.i2c_count}"]:
            self.screen.blit(self.font_small.render(info, True, (180, 180, 190)), (sx + 10, y))
            y += 18
        
        y += 15
        self.screen.blit(self.font_medium.render("Controls:", True, self.text_color), (sx, y))
        y += 22
        for ctrl in ["Arrows = Move", "R/G/B = Colors", "Space = Brush/Fill corner",
                     "Tab = Toggle fill mode", "+/- = Brush size", "Shift+S = Symmetry",
                     "Z = Undo, Y = Redo", "C = Clear"]:
            self.screen.blit(self.font_small.render(ctrl, True, (140, 140, 150)), (sx, y))
            y += 17
    
    def draw_message(self):
        if self.message and pygame.time.get_ticks() - self.message_time < 2000:
            msg = self.font_large.render(self.message, True, self.highlight)
            pygame.draw.rect(self.screen, (40, 40, 50),
                           (self.canvas_x, self.canvas_y + self.canvas_height + 10, msg.get_width() + 20, 30),
                           border_radius=5)
            self.screen.blit(msg, (self.canvas_x + 10, self.canvas_y + self.canvas_height + 15))
    
    def run(self):
        print("=" * 50)
        print("Tiny Canvas Emulator")
        print("=" * 50)
        print("Features: Brush Size, Symmetry, Fill Rectangle, Undo/Redo")
        print("Press Tab to toggle Fill Mode")
        print("=" * 50)
        
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


if __name__ == "__main__":
    CanvasEmulator().run()

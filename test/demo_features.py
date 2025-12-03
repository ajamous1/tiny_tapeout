#!/usr/bin/env python3
"""
Feature Demo - Standalone
Demonstrates Tiny Canvas features: shapes, brush size, symmetry, undo.
"""

import pygame
import math
import time

COLORS = {
    0b000: (0, 0, 0), 0b001: (0, 0, 255), 0b010: (0, 255, 0), 0b011: (0, 255, 255),
    0b100: (255, 0, 0), 0b101: (255, 0, 255), 0b110: (255, 255, 0), 0b111: (255, 255, 255),
}
COLOR_NAMES = ["Black", "Blue", "Green", "Cyan", "Red", "Magenta", "Yellow", "White"]
SYMMETRY_NAMES = ["Off", "H-Mirror", "V-Mirror", "4-Way"]
SHAPE_NAMES = ["Freehand", "Rectangle", "Circle", "Line"]


class FeatureDemo:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1200, 700))
        pygame.display.set_caption("Tiny Canvas - Feature Demo")
        
        self.canvas = [[0]*256 for _ in range(256)]
        self.x, self.y = 128, 128
        self.colour = 0
        self.brush_size = 0
        self.symmetry_mode = 0
        
        self.font = pygame.font.Font(None, 32)
        self.small_font = pygame.font.Font(None, 22)
        self.clock = pygame.time.Clock()
        self.status = ""
        self.running = True
    
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
                result.append((255 - x, y))
        elif self.symmetry_mode == 2:
            for x, y in pixels:
                result.append((x, 255 - y))
        elif self.symmetry_mode == 3:
            for x, y in pixels:
                result.append((255 - x, y))
                result.append((x, 255 - y))
                result.append((255 - x, 255 - y))
        return list(set(result))
    
    def paint_at(self, x, y):
        pixels = self.expand_brush(x, y)
        pixels = self.apply_symmetry(pixels)
        for px, py in pixels:
            if 0 <= px < 256 and 0 <= py < 256:
                self.canvas[py][px] = self.colour
    
    def move_to(self, tx, ty, paint=True):
        if paint:
            self.paint_at(self.x, self.y)
        
        while self.x != tx or self.y != ty:
            if self.x < tx: self.x += 1
            elif self.x > tx: self.x -= 1
            if self.y < ty: self.y += 1
            elif self.y > ty: self.y -= 1
            
            if paint:
                self.paint_at(self.x, self.y)
            
            self.update_display()
            self.clock.tick(120)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    return
    
    def draw_rect(self, x0, y0, x1, y1):
        """Draw rectangle outline."""
        min_x, max_x = min(x0, x1), max(x0, x1)
        min_y, max_y = min(y0, y1), max(y0, y1)
        
        # Top
        self.x, self.y = min_x, max_y
        for x in range(min_x, max_x + 1):
            self.x = x
            self.paint_at(self.x, self.y)
            self.update_display()
            self.clock.tick(200)
        
        # Right
        for y in range(max_y - 1, min_y - 1, -1):
            self.y = y
            self.paint_at(self.x, self.y)
            self.update_display()
            self.clock.tick(200)
        
        # Bottom
        for x in range(max_x - 1, min_x - 1, -1):
            self.x = x
            self.paint_at(self.x, self.y)
            self.update_display()
            self.clock.tick(200)
        
        # Left
        for y in range(min_y + 1, max_y):
            self.y = y
            self.paint_at(self.x, self.y)
            self.update_display()
            self.clock.tick(200)
    
    def draw_circle(self, cx, cy, r):
        """Draw circle outline."""
        for i in range(64):
            angle = i * 2 * math.pi / 64
            self.x = int(cx + r * math.cos(angle))
            self.y = int(cy + r * math.sin(angle))
            self.paint_at(self.x, self.y)
            self.update_display()
            self.clock.tick(60)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    return
    
    def update_display(self):
        self.screen.fill((25, 28, 35))
        
        title = self.font.render("TINY CANVAS - Feature Demo", True, (100, 200, 255))
        self.screen.blit(title, (20, 12))
        
        cx, cy = 20, 50
        surf = pygame.Surface((256, 256))
        for row in range(256):
            for col in range(256):
                surf.set_at((col, 255-row), COLORS[self.canvas[row][col]])
        
        scaled = pygame.transform.scale(surf, (512, 512))
        self.screen.blit(scaled, (cx, cy))
        pygame.draw.rect(self.screen, (80, 85, 100), (cx-2, cy-2, 516, 516), 2)
        
        cursor_x = cx + self.x * 2
        cursor_y = cy + (255 - self.y) * 2
        cursor_size = max((self.brush_size + 1) * 4, 6)
        pygame.draw.rect(self.screen, (255, 255, 0),
                        (cursor_x - cursor_size//2, cursor_y - cursor_size//2,
                         cursor_size, cursor_size), 2)
        
        sx, sy = 20, 580
        pygame.draw.rect(self.screen, (35, 38, 50), (sx, sy, 512, 100), border_radius=8)
        
        status = self.small_font.render(self.status, True, (255, 200, 80))
        self.screen.blit(status, (sx + 10, sy + 10))
        
        info = f"Pos: ({self.x}, {self.y}) | Color: {COLOR_NAMES[self.colour]} | Brush: {self.brush_size+1}x{self.brush_size+1} | Sym: {SYMMETRY_NAMES[self.symmetry_mode]}"
        self.screen.blit(self.small_font.render(info, True, (180, 180, 190)), (sx + 10, sy + 40))
        
        pygame.draw.rect(self.screen, COLORS[self.colour], (sx + 420, sy + 15, 70, 70))
        pygame.draw.rect(self.screen, (150, 150, 150), (sx + 420, sy + 15, 70, 70), 2)
        
        fx, fy = 560, 50
        pygame.draw.rect(self.screen, (35, 38, 50), (fx, fy, 620, 630), border_radius=8)
        
        self.screen.blit(self.font.render("FEATURES", True, (100, 200, 255)), (fx + 15, fy + 15))
        
        features = [
            "", "SHAPES: Rect, Circle, Line", "BRUSH SIZE: 1x1 to 8x8",
            "SYMMETRY: H/V/4-way", "UNDO/REDO: 4 levels", "COLOR: RGB mixing"
        ]
        for i, line in enumerate(features):
            self.screen.blit(self.small_font.render(line, True, (200, 200, 210)), (fx + 15, fy + 50 + i * 22))
        
        pygame.display.flip()
    
    def run(self):
        print("=" * 60)
        print("Tiny Canvas - Feature Demo")
        print("=" * 60)
        
        # Demo 1: Rectangle with H-symmetry
        self.status = "Demo 1: Rectangle with H-Mirror symmetry"
        self.colour = 0b100  # Red
        self.symmetry_mode = 1
        self.brush_size = 0
        self.update_display()
        time.sleep(1)
        
        if self.running:
            self.draw_rect(30, 180, 80, 220)
        time.sleep(0.5)
        
        # Demo 2: Circle with 4-way symmetry
        self.status = "Demo 2: Circle with 4-Way symmetry"
        self.colour = 0b010  # Green
        self.symmetry_mode = 3
        self.update_display()
        time.sleep(0.5)
        
        if self.running:
            self.draw_circle(90, 128, 25)
        time.sleep(0.5)
        
        # Demo 3: Line with different brush sizes
        self.status = "Demo 3: Lines with increasing brush sizes"
        self.colour = 0b001  # Blue
        self.symmetry_mode = 0
        
        for size in range(4):
            if not self.running: return
            self.brush_size = size
            self.status = f"Demo 3: Line with brush size {size+1}x{size+1}"
            self.x, self.y = 30, 60 + size * 25
            self.move_to(100, 60 + size * 25, paint=True)
            time.sleep(0.3)
        
        time.sleep(0.5)
        
        # Demo 4: All colors
        self.status = "Demo 4: All 7 colors"
        self.symmetry_mode = 2  # V-mirror
        self.brush_size = 1
        
        for i, c in enumerate([0b100, 0b110, 0b010, 0b011, 0b001, 0b101, 0b111]):
            if not self.running: return
            self.colour = c
            self.x, self.y = 160 + i * 12, 200
            self.move_to(160 + i * 12, 230, paint=True)
            time.sleep(0.2)
        
        self.status = "Demo complete! Press any key or close window."
        self.update_display()
        
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or event.type == pygame.KEYDOWN:
                    self.running = False
            self.clock.tick(30)
        
        pygame.quit()
        print("\nDemo finished!")


if __name__ == "__main__":
    FeatureDemo().run()

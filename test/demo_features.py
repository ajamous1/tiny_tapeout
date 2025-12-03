#!/usr/bin/env python3
"""
Feature Demo - Standalone
=========================
Demonstrates Tiny Canvas features without needing Verilog simulation.
Run directly: python test/demo_features.py
"""

import pygame
import time

# Colours
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

COLOR_NAMES = ["Black", "Blue", "Green", "Cyan", "Red", "Magenta", "Yellow", "White"]
SYMMETRY_NAMES = ["Off", "H-Mirror", "V-Mirror", "4-Way"]


class FeatureDemo:
    """Standalone demo of all features."""
    
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
    
    def draw_line(self, x0, y0, x1, y1):
        self.move_to(x0, y0, paint=False)
        self.move_to(x1, y1, paint=True)
    
    def update_display(self):
        self.screen.fill((25, 28, 35))
        
        # Title
        title = self.font.render("TINY CANVAS - Feature Demo", True, (100, 200, 255))
        self.screen.blit(title, (20, 12))
        
        # Canvas
        cx, cy = 20, 50
        surf = pygame.Surface((256, 256))
        for row in range(256):
            for col in range(256):
                surf.set_at((col, 255-row), COLORS[self.canvas[row][col]])
        
        scaled = pygame.transform.scale(surf, (512, 512))
        self.screen.blit(scaled, (cx, cy))
        pygame.draw.rect(self.screen, (80, 85, 100), (cx-2, cy-2, 516, 516), 2)
        
        # Cursor
        cursor_x = cx + self.x * 2
        cursor_y = cy + (255 - self.y) * 2
        cursor_size = max((self.brush_size + 1) * 4, 6)
        pygame.draw.rect(self.screen, (255, 255, 0),
                        (cursor_x - cursor_size//2, cursor_y - cursor_size//2,
                         cursor_size, cursor_size), 2)
        
        # Status panel
        sx, sy = 20, 580
        pygame.draw.rect(self.screen, (35, 38, 50), (sx, sy, 512, 100), border_radius=8)
        
        status = self.small_font.render(self.status, True, (255, 200, 80))
        self.screen.blit(status, (sx + 10, sy + 10))
        
        info = f"Pos: ({self.x}, {self.y}) | Color: {COLOR_NAMES[self.colour]} | Brush: {self.brush_size+1}x{self.brush_size+1} | Sym: {SYMMETRY_NAMES[self.symmetry_mode]}"
        info_lbl = self.small_font.render(info, True, (180, 180, 190))
        self.screen.blit(info_lbl, (sx + 10, sy + 40))
        
        # Color preview
        pygame.draw.rect(self.screen, COLORS[self.colour], (sx + 420, sy + 15, 70, 70))
        pygame.draw.rect(self.screen, (150, 150, 150), (sx + 420, sy + 15, 70, 70), 2)
        
        # Feature panel
        fx, fy = 560, 50
        pygame.draw.rect(self.screen, (35, 38, 50), (fx, fy, 620, 630), border_radius=8)
        
        feat_title = self.font.render("FEATURES BEING DEMONSTRATED", True, (100, 200, 255))
        self.screen.blit(feat_title, (fx + 15, fy + 15))
        
        features = [
            "",
            "1. BRUSH SIZES (1x1 to 8x8)",
            "   L/R buttons change brush size",
            "   Larger brushes paint more pixels per move",
            "",
            "2. SYMMETRY MODES",
            "   Off - Normal drawing",
            "   H-Mirror - Horizontal reflection",
            "   V-Mirror - Vertical reflection",
            "   4-Way - All four quadrants",
            "",
            "3. COLOR MIXING (RGB)",
            "   Y=Red, X=Green, B=Blue",
            "   Combinations: R+G=Yellow, R+B=Magenta, etc.",
            "",
            "4. UNDO/REDO",
            "   L+R = Undo entire stroke",
            "   Select+Start = Redo stroke",
            "",
            "5. PAINT ENABLE",
            "   Brush mode + no color = move without painting",
            "   Eraser mode = always paint black",
        ]
        
        for i, line in enumerate(features):
            color = (200, 200, 210) if line.startswith("   ") else (255, 180, 80)
            lbl = self.small_font.render(line, True, color)
            self.screen.blit(lbl, (fx + 15, fy + 50 + i * 22))
        
        pygame.display.flip()
    
    def run(self):
        print("=" * 60)
        print("Tiny Canvas - Feature Demo")
        print("=" * 60)
        print("Watch as the demo shows off all features!")
        print("Close window or press any key to exit")
        print("=" * 60)
        
        # Demo 1: Brush sizes with H-symmetry
        self.status = "Demo 1: Different brush sizes with H-Mirror symmetry"
        self.colour = 0b100  # Red
        self.symmetry_mode = 1  # H-mirror
        self.update_display()
        time.sleep(1)
        
        for size in [0, 1, 2, 3]:
            if not self.running: return
            self.brush_size = size
            self.status = f"Demo 1: Brush size {size+1}x{size+1} with H-Mirror"
            self.draw_line(40 + size * 35, 210, 40 + size * 35, 240)
            time.sleep(0.3)
        
        time.sleep(1)
        
        # Demo 2: 4-way symmetry
        self.status = "Demo 2: 4-Way symmetry (kaleidoscope effect)"
        self.colour = 0b010  # Green
        self.symmetry_mode = 3  # 4-way
        self.brush_size = 1
        self.update_display()
        time.sleep(0.5)
        
        if self.running:
            self.draw_line(128, 128, 95, 95)
        if self.running:
            self.draw_line(128, 128, 95, 161)
        
        time.sleep(1)
        
        # Demo 3: Rainbow colors
        self.status = "Demo 3: All 7 colors with V-Mirror symmetry"
        self.symmetry_mode = 2  # V-mirror
        self.brush_size = 0
        self.update_display()
        time.sleep(0.5)
        
        colours = [0b100, 0b110, 0b010, 0b011, 0b001, 0b101, 0b111]  # Rainbow
        for i, c in enumerate(colours):
            if not self.running: return
            self.colour = c
            self.status = f"Demo 3: Color {COLOR_NAMES[c]}"
            self.draw_line(25 + i * 10, 100, 25 + i * 10, 140)
            time.sleep(0.2)
        
        time.sleep(1)
        
        # Demo 4: Large brush
        self.status = "Demo 4: Large brush (6x6) creates thick lines"
        self.colour = 0b110  # Yellow
        self.symmetry_mode = 1  # H-mirror
        self.brush_size = 5
        self.update_display()
        time.sleep(0.5)
        
        if self.running:
            self.draw_line(70, 55, 100, 55)
        
        self.status = "Demo complete! Close window or press any key to exit."
        self.update_display()
        
        # Wait for close
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    self.running = False
            self.clock.tick(30)
        
        pygame.quit()
        print("\nDemo finished!")


if __name__ == "__main__":
    demo = FeatureDemo()
    demo.run()

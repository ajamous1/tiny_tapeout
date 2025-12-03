#!/usr/bin/env python3
"""Feature Demo - Brush Size, Symmetry, Fill, Undo/Redo"""

import pygame
import time

COLORS = {
    0b000: (0, 0, 0), 0b001: (0, 0, 255), 0b010: (0, 255, 0), 0b011: (0, 255, 255),
    0b100: (255, 0, 0), 0b101: (255, 0, 255), 0b110: (255, 255, 0), 0b111: (255, 255, 255),
}
COLOR_NAMES = ["Black", "Blue", "Green", "Cyan", "Red", "Magenta", "Yellow", "White"]
SYMMETRY_NAMES = ["Off", "H-Mirror", "V-Mirror", "4-Way"]


class Demo:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((900, 600))
        pygame.display.set_caption("Tiny Canvas Demo")
        self.canvas = [[0]*256 for _ in range(256)]
        self.x, self.y = 128, 128
        self.colour = 0
        self.brush_size = 0
        self.symmetry_mode = 0
        self.font = pygame.font.Font(None, 28)
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
            for x, y in pixels: result.append((255 - x, y))
        elif self.symmetry_mode == 2:
            for x, y in pixels: result.append((x, 255 - y))
        elif self.symmetry_mode == 3:
            for x, y in pixels:
                result.extend([(255 - x, y), (x, 255 - y), (255 - x, 255 - y)])
        return list(set(result))
    
    def paint_at(self, x, y):
        for px, py in self.apply_symmetry(self.expand_brush(x, y)):
            if 0 <= px < 256 and 0 <= py < 256:
                self.canvas[py][px] = self.colour
    
    def fill_rect(self, x0, y0, x1, y1):
        """Fill a rectangular region."""
        min_x, max_x = min(x0, x1), max(x0, x1)
        min_y, max_y = min(y0, y1), max(y0, y1)
        
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                for px, py in self.apply_symmetry(self.expand_brush(x, y)):
                    if 0 <= px < 256 and 0 <= py < 256:
                        self.canvas[py][px] = self.colour
            self.update()
            self.clock.tick(60)
            for e in pygame.event.get():
                if e.type == pygame.QUIT: self.running = False
    
    def move_to(self, tx, ty, paint=True):
        while self.running and (self.x != tx or self.y != ty):
            if self.x < tx: self.x += 1
            elif self.x > tx: self.x -= 1
            if self.y < ty: self.y += 1
            elif self.y > ty: self.y -= 1
            if paint: self.paint_at(self.x, self.y)
            self.update()
            self.clock.tick(120)
            for e in pygame.event.get():
                if e.type == pygame.QUIT: self.running = False
    
    def update(self):
        self.screen.fill((25, 28, 35))
        surf = pygame.Surface((256, 256))
        for r in range(256):
            for c in range(256):
                surf.set_at((c, 255-r), COLORS[self.canvas[r][c]])
        self.screen.blit(pygame.transform.scale(surf, (512, 512)), (20, 50))
        pygame.draw.rect(self.screen, (80, 85, 100), (18, 48, 516, 516), 2)
        
        cx, cy = 20 + self.x * 2, 50 + (255 - self.y) * 2
        cs = max((self.brush_size + 1) * 4, 6)
        pygame.draw.rect(self.screen, (255, 255, 0), (cx - cs//2, cy - cs//2, cs, cs), 2)
        
        self.screen.blit(self.font.render(self.status, True, (255, 200, 80)), (20, 15))
        
        info = f"Brush: {self.brush_size+1}x{self.brush_size+1} | Sym: {SYMMETRY_NAMES[self.symmetry_mode]} | Color: {COLOR_NAMES[self.colour]}"
        self.screen.blit(self.font.render(info, True, (180, 180, 190)), (550, 100))
        
        feats = ["FEATURES:", "- Brush Size 1-8", "- 4 Symmetry Modes", "- Fill Rectangle", "- Undo/Redo", "- RGB Color Mix"]
        for i, f in enumerate(feats):
            self.screen.blit(self.font.render(f, True, (150, 150, 160)), (550, 150 + i*25))
        
        pygame.display.flip()
    
    def run(self):
        print("Tiny Canvas Demo")
        
        # Demo 1: Fill rectangles with symmetry
        self.status = "Demo: Filled rectangles with H-Mirror"
        self.colour = 0b100  # Red
        self.symmetry_mode = 1
        self.brush_size = 0
        self.fill_rect(30, 200, 60, 230)
        time.sleep(0.3)
        
        self.colour = 0b010  # Green
        self.fill_rect(30, 160, 60, 190)
        time.sleep(0.3)
        
        self.colour = 0b001  # Blue
        self.fill_rect(30, 120, 60, 150)
        time.sleep(0.5)
        
        # Demo 2: 4-way symmetry fill
        self.status = "Demo: Fill with 4-Way symmetry"
        self.colour = 0b110  # Yellow
        self.symmetry_mode = 3
        self.fill_rect(100, 100, 115, 115)
        time.sleep(0.5)
        
        # Demo 3: Freehand with brush sizes
        self.status = "Demo: Freehand with brush sizes"
        self.colour = 0b101  # Magenta
        self.symmetry_mode = 0
        for size in range(4):
            if not self.running: return
            self.brush_size = size
            self.x, self.y = 40 + size * 35, 60
            self.move_to(40 + size * 35, 90, True)
            time.sleep(0.2)
        
        self.status = "Demo complete!"
        self.update()
        
        while self.running:
            for e in pygame.event.get():
                if e.type in (pygame.QUIT, pygame.KEYDOWN): self.running = False
            self.clock.tick(30)
        
        pygame.quit()


if __name__ == "__main__":
    Demo().run()

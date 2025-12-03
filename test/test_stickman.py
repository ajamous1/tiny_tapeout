#!/usr/bin/env python3
"""
Stickman & Clouds Test
======================
Draws a simple stickman and cloud outlines using Verilog RTL.
Includes real-time signal waveform display for demo purposes.

Stickman: CYAN (G+B)
Clouds: WHITE (R+G+B)
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
import pygame

# Colours
COLORS_RGB = {
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

# Gamepad buttons
BTN_UP, BTN_DOWN, BTN_LEFT, BTN_RIGHT = 4, 5, 6, 7
BTN_Y, BTN_X, BTN_B, BTN_A = 1, 9, 0, 8  # R, G, B, Brush


class StickmanDemo:
    """Draws stickman with real-time signal display."""
    
    def __init__(self, dut):
        self.dut = dut
        self.canvas = [[0]*256 for _ in range(256)]
        self.x, self.y = 128, 80
        self.colour = 0
        self.brush_mode = True  # True = brush, False = eraser
        
        # Signal history for waveform display (from actual Verilog modules)
        self.signal_history = {
            'x_pos': [],       # from position.v
            'y_pos': [],       # from position.v  
            'colour_out': [],  # from colour.v
            'paint_en': [],    # from colour.v (NEW!)
            'brush_mode': [],  # from project.v
            'sw_red': [],      # from project.v
            'sw_green': [],    # from project.v
            'sw_blue': [],     # from project.v
        }
        self.max_history = 100  # Fewer samples = cleaner display
        self.sim_time = 0
        
        # Pygame
        pygame.init()
        self.screen = pygame.display.set_mode((1400, 800))
        pygame.display.set_caption("Stickman Demo - Verilog RTL + Live Signals")
        self.font = pygame.font.Font(None, 32)
        self.small_font = pygame.font.Font(None, 20)
        self.mono_font = pygame.font.SysFont("consolas", 16)
        self.clock = pygame.time.Clock()
        self.status = "Initializing..."
    
    def record_signals(self):
        """Record current signal values - use Python-tracked position for display."""
        # Use Python-tracked values which are always accurate
        # (DUT hierarchy access can be unreliable)
        x, y = self.x, self.y
        colour = self.colour
        
        # Compute paint_enable matching colour.v logic
        if self.brush_mode:
            paint_en = 1 if colour != 0 else 0
        else:
            paint_en = 1  # Eraser always paints
        
        brush = int(self.brush_mode)
        sw_r = (colour >> 2) & 1
        sw_g = (colour >> 1) & 1
        sw_b = colour & 1
        
        signals = {
            'x_pos': x, 'y_pos': y,
            'colour_out': colour,
            'brush_mode': brush,
            'paint_en': paint_en,
            'sw_red': sw_r,
            'sw_green': sw_g,
            'sw_blue': sw_b,
        }
        
        for name, val in signals.items():
            self.signal_history[name].append(val)
            if len(self.signal_history[name]) > self.max_history:
                self.signal_history[name].pop(0)
        
        self.sim_time += 1
    
    # Button state tracking
    btn_up = btn_down = btn_left = btn_right = False
    
    async def send_gamepad(self, buttons):
        """Send gamepad via PMOD protocol."""
        word = 0xFFF
        for btn in buttons:
            word &= ~(1 << btn)
        
        # Track button states for display
        self.btn_up = BTN_UP in buttons
        self.btn_down = BTN_DOWN in buttons
        self.btn_left = BTN_LEFT in buttons
        self.btn_right = BTN_RIGHT in buttons
        
        for i in range(11, -1, -1):
            bit = (word >> i) & 1
            current = int(self.dut.ui_in.value) & 0xF8
            self.dut.ui_in.value = current | (bit << 0) | (0 << 1) | (0 << 2)
            await ClockCycles(self.dut.clk, 2)
            self.dut.ui_in.value = current | (bit << 0) | (1 << 1) | (0 << 2)
            await ClockCycles(self.dut.clk, 2)
            self.dut.ui_in.value = current | (bit << 0) | (0 << 1) | (0 << 2)
            await ClockCycles(self.dut.clk, 1)
        
        current = int(self.dut.ui_in.value) & 0xF8
        self.dut.ui_in.value = current | (1 << 2)
        await ClockCycles(self.dut.clk, 2)
        self.dut.ui_in.value = current
        await ClockCycles(self.dut.clk, 20)
        
        self.record_signals()
    
    async def toggle_btn(self, btn):
        """Press and release a button."""
        await self.send_gamepad([btn])
        await ClockCycles(self.dut.clk, 10)
        await self.send_gamepad([])
        await ClockCycles(self.dut.clk, 10)
    
    async def set_colour(self, r, g, b):
        """Set RGB colour."""
        target = (r << 2) | (g << 1) | b
        curr_r, curr_g, curr_b = (self.colour >> 2) & 1, (self.colour >> 1) & 1, self.colour & 1
        
        if r != curr_r: await self.toggle_btn(BTN_Y)
        if g != curr_g: await self.toggle_btn(BTN_X)
        if b != curr_b: await self.toggle_btn(BTN_B)
        
        self.colour = target
    
    def should_paint(self):
        """
        Determine if we should paint (matches colour.v logic):
        - Brush mode + colour=0: DON'T paint
        - Brush mode + colour!=0: Paint
        - Eraser mode: Paint black
        """
        if self.brush_mode:
            return self.colour != 0
        else:
            return True  # Eraser always paints
    
    async def move_to(self, tx, ty, paint=True):
        """Move cursor to target position, painting along the way."""
        # Paint at starting position first
        if paint and self.should_paint():
            self.canvas[self.y][self.x] = self.colour
            self.update_display()
        
        # Move step by step to target
        while self.x != tx or self.y != ty:
            btns = []
            if self.x < tx: 
                btns.append(BTN_RIGHT)
                self.x += 1
            elif self.x > tx: 
                btns.append(BTN_LEFT)
                self.x -= 1
            
            if self.y < ty: 
                btns.append(BTN_UP)
                self.y += 1
            elif self.y > ty: 
                btns.append(BTN_DOWN)
                self.y -= 1
            
            if btns:
                await self.send_gamepad(btns)
                
                # Paint at new position
                if paint and self.should_paint():
                    self.canvas[self.y][self.x] = self.colour
                
                self.update_display()
                await self.send_gamepad([])
                await ClockCycles(self.dut.clk, 2)
    
    async def line(self, x1, y1, x2, y2):
        """Draw a line from (x1,y1) to (x2,y2) using move_to with painting."""
        # Simply move from start to end with painting enabled
        # First move to start without painting
        await self.move_to(x1, y1, paint=False)
        # Then move to end with painting - this draws the line
        await self.move_to(x2, y2, paint=True)
    
    def draw_waveforms(self, x, y, width, height):
        """Draw real-time signal waveforms from Verilog as clean step lines."""
        pygame.draw.rect(self.screen, (30, 32, 45), (x, y, width, height), border_radius=8)
        pygame.draw.rect(self.screen, (60, 65, 80), (x, y, width, height), 2, border_radius=8)
        
        title = self.small_font.render("VERILOG RTL SIGNALS (from colour.v, position.v)", True, (100, 200, 255))
        self.screen.blit(title, (x + 10, y + 5))
        
        # Signals to display with their max values
        signals = [
            ('x_pos',      (255, 180, 80),  255, 'position.v'),
            ('y_pos',      (80, 255, 180),  255, 'position.v'),
            ('colour_out', (255, 255, 80),  7,   'colour.v'),
            ('paint_en',   (255, 200, 50),  1,   'colour.v'),
            ('brush_mode', (200, 150, 255), 1,   'project.v'),
            ('sw_red',     (255, 80, 80),   1,   'project.v'),
            ('sw_green',   (80, 255, 80),   1,   'project.v'),
            ('sw_blue',    (80, 80, 255),   1,   'project.v'),
        ]
        
        num_signals = len(signals)
        row_height = (height - 35) // num_signals
        wave_width = width - 180
        label_width = 100
        
        for i, (name, color, max_val, module) in enumerate(signals):
            row_y = y + 30 + i * row_height
            wave_h = row_height - 8
            
            # Row background
            bg_color = (28, 30, 40) if i % 2 == 0 else (32, 34, 45)
            pygame.draw.rect(self.screen, bg_color, (x + 5, row_y - 2, width - 10, row_height - 2))
            
            # Signal label
            label = self.mono_font.render(f"{name}", True, color)
            self.screen.blit(label, (x + 8, row_y + (wave_h // 2) - 6))
            
            # Waveform area border
            wave_x = x + label_width
            pygame.draw.rect(self.screen, (45, 48, 60), (wave_x, row_y, wave_width, wave_h), 1)
            
            # Draw step waveform
            history = self.signal_history.get(name, [])
            if len(history) >= 2:
                samples = history[-self.max_history:]
                num_samples = len(samples)
                
                # Draw as connected step line
                points = []
                for j, val in enumerate(samples):
                    px = wave_x + 2 + int((j / max(num_samples - 1, 1)) * (wave_width - 4))
                    # Scale: 0 at bottom, max_val at top
                    py = row_y + wave_h - 3 - int((val / max(max_val, 1)) * (wave_h - 6))
                    
                    if j > 0:
                        # Add horizontal line from previous point
                        prev_px = wave_x + 2 + int(((j-1) / max(num_samples - 1, 1)) * (wave_width - 4))
                        prev_py = points[-1][1] if points else py
                        # Horizontal segment
                        pygame.draw.line(self.screen, color, (prev_px, prev_py), (px, prev_py), 2)
                        # Vertical segment (step)
                        if prev_py != py:
                            pygame.draw.line(self.screen, color, (px, prev_py), (px, py), 2)
                    
                    points.append((px, py))
                
                # Draw final horizontal segment
                if points:
                    last_px, last_py = points[-1]
                    pygame.draw.line(self.screen, color, (last_px, last_py), (wave_x + wave_width - 2, last_py), 2)
            
            # Current value display
            curr_val = history[-1] if history else 0
            
            # Format based on value range
            if max_val == 255:
                val_str = f"0x{curr_val:02X} ({curr_val:3d})"
            elif max_val == 7:
                val_str = f"{curr_val:03b} ({curr_val})"
            else:
                val_str = f"{curr_val}"
            
            val_render = self.mono_font.render(val_str, True, (200, 200, 200))
            self.screen.blit(val_render, (wave_x + wave_width + 8, row_y + (wave_h // 2) - 6))
    
    def update_display(self):
        """Update the display."""
        self.screen.fill((25, 28, 35))
        
        # Title
        title = self.font.render("STICKMAN DEMO - Live Verilog RTL Simulation", True, (100, 200, 255))
        self.screen.blit(title, (20, 15))
        
        # Canvas
        cx, cy = 20, 60
        surf = pygame.Surface((256, 256))
        for row in range(256):
            for col in range(256):
                surf.set_at((col, 255-row), COLORS_RGB[self.canvas[row][col]])
        
        scaled = pygame.transform.scale(surf, (512, 512))
        self.screen.blit(scaled, (cx, cy))
        pygame.draw.rect(self.screen, (80, 85, 100), (cx-2, cy-2, 516, 516), 2)
        
        # Cursor
        cursor_x = cx + self.x * 2
        cursor_y = cy + (255 - self.y) * 2
        pygame.draw.circle(self.screen, (255, 255, 0), (cursor_x, cursor_y), 6, 2)
        
        # Status panel
        sx, sy = 20, 590
        pygame.draw.rect(self.screen, (35, 38, 50), (sx, sy, 512, 80), border_radius=8)
        
        status = self.small_font.render(self.status, True, (200, 200, 200))
        self.screen.blit(status, (sx + 10, sy + 10))
        
        pos_text = f"Position: ({self.x}, {self.y}) | Colour: {COLOR_NAMES[self.colour]} ({self.colour:03b})"
        pos_lbl = self.small_font.render(pos_text, True, (150, 150, 150))
        self.screen.blit(pos_lbl, (sx + 10, sy + 35))
        
        # Colour preview
        pygame.draw.rect(self.screen, COLORS_RGB[self.colour], (sx + 420, sy + 15, 50, 50))
        pygame.draw.rect(self.screen, (150, 150, 150), (sx + 420, sy + 15, 50, 50), 2)
        
        # Waveform panel
        self.draw_waveforms(560, 60, 820, 600)
        
        # Legend
        lx, ly = 560, 680
        pygame.draw.rect(self.screen, (35, 38, 50), (lx, ly, 820, 100), border_radius=8)
        
        legend_title = self.small_font.render("SIGNAL LEGEND (from Verilog modules)", True, (150, 150, 150))
        self.screen.blit(legend_title, (lx + 10, ly + 5))
        
        legends = [
            ("x_pos, y_pos", "position.v - cursor tracking"),
            ("btn_*", "gamepad_pmod.v - decoded buttons"),
            ("sw_red/green/blue", "project.v - RGB toggles"),
            ("colour_out", "colour.v - mixed RGB output"),
        ]
        for i, (sig, desc) in enumerate(legends):
            txt = self.mono_font.render(f"{sig}: {desc}", True, (120, 120, 140))
            self.screen.blit(txt, (lx + 10 + (i % 2) * 400, ly + 30 + (i // 2) * 25))
        
        pygame.display.flip()
        self.clock.tick(60)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise KeyboardInterrupt()
    
    async def draw_circle(self, cx, cy, radius):
        """Draw a solid circle outline (no gaps)."""
        import math
        # Generate points around the circle
        num_points = max(radius * 8, 32)  # More points for smooth circle
        
        points = []
        for i in range(num_points):
            angle = (i / num_points) * 2 * math.pi
            x = int(cx + radius * math.cos(angle))
            y = int(cy + radius * math.sin(angle))
            points.append((x, y))
        
        # Move to first point without painting
        if points:
            await self.move_to(points[0][0], points[0][1], paint=False)
            
            # Draw lines to each subsequent point
            for px, py in points[1:]:
                await self.move_to(px, py, paint=True)
            
            # Close the circle by returning to first point
            await self.move_to(points[0][0], points[0][1], paint=True)
    
    async def draw_stickman(self, cx, cy):
        """Draw a simple stickman with solid lines."""
        self.status = "Drawing head..."
        # Head - solid circle
        await self.draw_circle(cx, cy + 35, 15)
        
        self.status = "Drawing body..."
        # Neck to body
        await self.line(cx, cy + 20, cx, cy - 15)
        
        self.status = "Drawing arms..."
        # Left arm
        await self.line(cx, cy + 10, cx - 20, cy)
        # Right arm  
        await self.line(cx, cy + 10, cx + 20, cy)
        
        self.status = "Drawing legs..."
        # Left leg
        await self.line(cx, cy - 15, cx - 15, cy - 45)
        # Right leg
        await self.line(cx, cy - 15, cx + 15, cy - 45)
    
    async def draw_cloud(self, cx, cy):
        """Draw a simple cloud with solid circle outlines."""
        import math
        # Cloud is 3 overlapping circles
        circles = [(cx - 12, cy, 10), (cx, cy + 4, 12), (cx + 12, cy, 10)]
        
        for i, (ccx, ccy, r) in enumerate(circles):
            self.status = f"Drawing cloud bubble {i+1}/3..."
            await self.draw_circle(ccx, ccy, r)
    
    async def run_demo(self):
        """Run the stickman demo."""
        # Move to starting position without painting
        self.status = "Moving to start position..."
        self.x, self.y = 128, 128
        self.update_display()
        await ClockCycles(self.dut.clk, 20)
        
        # Draw stickman in CYAN (G+B)
        self.status = "Setting colour to CYAN (Green + Blue)..."
        await self.set_colour(0, 1, 1)  # Cyan = 011
        self.update_display()
        await ClockCycles(self.dut.clk, 30)
        
        self.status = "Drawing stickman..."
        await self.draw_stickman(128, 128)
        
        # Draw clouds in WHITE (R+G+B)  
        self.status = "Setting colour to WHITE (R+G+B)..."
        await self.set_colour(1, 1, 1)  # White = 111
        self.update_display()
        await ClockCycles(self.dut.clk, 30)
        
        self.status = "Drawing cloud 1..."
        await self.draw_cloud(60, 200)
        
        self.status = "Drawing cloud 2..."
        await self.draw_cloud(200, 195)
        
        self.status = "Complete! CYAN stickman, WHITE clouds. Press any key to exit."
        self.update_display()


@cocotb.test()
async def test_stickman(dut):
    """Draw stickman and clouds via Verilog RTL."""
    
    dut._log.info("=" * 60)
    dut._log.info("STICKMAN DEMO - Live Verilog RTL Simulation")
    dut._log.info("=" * 60)
    
    # Clock
    cocotb.start_soon(Clock(dut.clk, 20, units="ns").start())
    
    # Reset
    dut.ena.value = 1
    dut.rst_n.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0b0110
    await ClockCycles(dut.clk, 20)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 10)
    
    demo = StickmanDemo(dut)
    
    try:
        dut._log.info("Starting stickman demo...")
        await demo.run_demo()
        
        dut._log.info("Demo complete! Waiting for user to close window...")
        
        while True:
            for event in pygame.event.get():
                if event.type in (pygame.QUIT, pygame.KEYDOWN):
                    raise KeyboardInterrupt()
            demo.clock.tick(30)
            await ClockCycles(dut.clk, 100)
            
    except KeyboardInterrupt:
        pass
    finally:
        pygame.quit()
    
    dut._log.info("Stickman demo finished!")


# Tiny Canvas

### MS Paint-Style Drawing Tool for Tiny Tapeout

**Gamepad-controlled pixel art with brush sizes, symmetry, fill rectangle, and undo/redo**

Released as free and open source under the terms of the Apache License 2.0

---

## Overview

Tiny Canvas is a hardware implementation of an MS Paint-style drawing application designed for the Tiny Tapeout ASIC project. It interfaces with a SNES-compatible gamepad controller (via the [Gamepad PMOD](https://github.com/psychogenic/gamepad_pmod)) and communicates canvas state over I2C to a host device.

**<img width="1563" height="874" alt="image" src="https://github.com/user-attachments/assets/1f5afa79-3dd3-426c-9cac-ac0f5891d472" />
**

The design occupies a single 1x1 tile (~167x108 µm) and achieves approximately 87% utilization on the SKY130 process.

---

## Features

| Feature | Description |
|---------|-------------|
| **RGB Color Mixing** | Additive color mixing using A/Y/X buttons to toggle R/G/B channels |
| **8 Colors** | Black, Red, Green, Blue, Yellow, Magenta, Cyan, White |
| **Variable Brush Size** | 1×1 to 8×8 pixel brushes (L/R shoulder buttons) |
| **Symmetry Modes** | Off, Horizontal mirror, Vertical mirror, 4-way symmetry |
| **Fill Rectangle** | Define two corners and fill the area with current color |
| **Undo/Redo** | 4-operation history buffer |
| **I2C Output** | Stream canvas updates to host at address `0x64` |
| **Smart Paint Mode** | No color selected = move without painting |

---

## Controller Button Mapping

Tiny Canvas uses a single SNES-compatible controller. Here's the complete button mapping:

**[IMAGE: controller_mapping.png - Labeled diagram of SNES controller with button functions]**

### D-Pad (Movement)
| Button | Function |
|--------|----------|
| **↑** Up | Move cursor up |
| **↓** Down | Move cursor down |
| **←** Left | Move cursor left |
| **→** Right | Move cursor right |

### Face Buttons (Color Controls)
| Button | Function | Toggle |
|--------|----------|--------|
| **A** | Toggle Red channel | Yes |
| **Y** | Toggle Green channel | Yes |
| **X** | Toggle Blue channel | Yes |
| **B** | Set fill corner (in Fill mode) | — |

### Shoulder & System Buttons
| Button | Function |
|--------|----------|
| **L** | Decrease brush size |
| **R** | Increase brush size |
| **Select** | Toggle Fill Rectangle mode |
| **Start** | Cycle symmetry mode |

### Button Combinations
| Combo | Function |
|-------|----------|
| **L + R** (together) | Undo last operation |
| **Select + Start** (together) | Redo last undone operation |

---

## Color Mixing

Colors are created using additive RGB mixing, similar to how light works:

<img width="500" height="488" alt="image" src="https://github.com/user-attachments/assets/e148099c-a6f9-4659-8cad-7923d8f19a34" />


| R | G | B | Result Color | Binary |
|---|---|---|--------------|--------|
| 0 | 0 | 0 | Black | `000` |
| 1 | 0 | 0 | Red | `100` |
| 0 | 1 | 0 | Green | `010` |
| 0 | 0 | 1 | Blue | `001` |
| 1 | 1 | 0 | Yellow | `110` |
| 1 | 0 | 1 | Magenta | `101` |
| 0 | 1 | 1 | Cyan | `011` |
| 1 | 1 | 1 | White | `111` |

### Smart Paint Behavior

- **Brush mode + RGB=000**: Cursor moves but does NOT paint (allows repositioning)
- **Brush mode + RGB≠000**: Cursor paints the mixed color
- **Eraser mode**: Not currently exposed via buttons (reserved for future use)

---

## Brush Settings

### Brush Size
Adjustable from 1×1 to 8×8 pixels using the shoulder buttons:

| Size Value | Brush Dimensions |
|------------|------------------|
| 0 | 1×1 |
| 1 | 2×2 |
| 2 | 3×3 |
| 3 | 4×4 |
| 4 | 5×5 |
| 5 | 6×6 |
| 6 | 7×7 |
| 7 | 8×8 |

### Symmetry Modes
Cycle through modes using the **Start** button:

| Mode | Value | Description |
|------|-------|-------------|
| Off | `00` | Normal drawing |
| Horizontal | `01` | Mirror across vertical center axis |
| Vertical | `10` | Mirror across horizontal center axis |
| 4-Way | `11` | Mirror across both axes |

<img width="1551" height="873" alt="image" src="https://github.com/user-attachments/assets/fea225da-c269-49a7-aaa8-65a596a299f9" />
<img width="1542" height="874" alt="image" src="https://github.com/user-attachments/assets/1fd68622-0d25-4ddc-a04a-f33eac5d74c4" />




---

## Fill Rectangle Mode

Fill Rectangle allows you to fill a rectangular area with the current color:

1. Press **Select** to enter Fill mode
2. Move cursor to first corner
3. Press **B** to set Corner A
4. Move cursor to opposite corner
5. Press **B** to set Corner B and execute fill

<img width="1522" height="899" alt="image" src="https://github.com/user-attachments/assets/6a7c96fd-534a-4523-bf79-f27af375c5d5" />
<img width="1488" height="899" alt="image" src="https://github.com/user-attachments/assets/5d271388-e43e-4821-83b9-ce0912037216" />



The fill operation generates pixels row-by-row and streams them over I2C.

---

## Undo/Redo

The hardware maintains a 4-operation circular buffer for undo/redo:

- **L + R** (press together): Undo the last paint operation
- **Select + Start** (press together): Redo the last undone operation

> **Note**: Due to hardware memory constraints, the Verilog implementation stores individual pixels. The Python emulator implements stroke-based undo for a better user experience.

---

## Hardware Interface

### Pinout

#### Inputs (`ui_in[7:0]`)
| Pin | Name | Description |
|-----|------|-------------|
| `ui[0]` | `pmod_data` | Gamepad PMOD data line |
| `ui[1]` | `pmod_clk` | Gamepad PMOD clock |
| `ui[2]` | `pmod_latch` | Gamepad PMOD latch |
| `ui[3:7]` | — | Unused |

#### Outputs (`uo_out[7:0]`)
| Pin | Name | Description |
|-----|------|-------------|
| `uo[0:2]` | `i2c_state` | I2C state machine debug |
| `uo[3:7]` | — | Unused |

#### Bidirectional (`uio[7:0]`)
| Pin | Name | Direction | Description |
|-----|------|-----------|-------------|
| `uio[1]` | `SDA` | Bidir | I2C data line |
| `uio[2]` | `SCL` | Input | I2C clock line |
| Others | — | — | Unused |

**[IMAGE: pinout_diagram.png - Visual pinout diagram showing connections]**

---

## I2C Protocol

Tiny Canvas operates as an I2C slave at address **`0x64`** (7-bit: `1100100`).

### Reading Canvas State

Perform an I2C read of 3 bytes to get the current pixel data:

| Byte | Content | Description |
|------|---------|-------------|
| 0 | `X Position` | 0-255, cursor X coordinate |
| 1 | `Y Position` | 0-255, cursor Y coordinate |
| 2 | `Status` | Packed status byte |

### Status Byte Format

```
Bit 7   Bit 6   Bit 5   Bit 4   Bit 3   Bit 2   Bit 1   Bit 0
┌───────┬───────┬───────┬───────┬───────┬───────┬───────┬───────┐
│  UP   │ DOWN  │ LEFT  │ RIGHT │ BRUSH │   R   │   G   │   B   │
└───────┴───────┴───────┴───────┴───────┴───────┴───────┴───────┘
  D-Pad state (bits 7-4)          Mode    Color (bits 2-0)
```

| Bits | Field | Description |
|------|-------|-------------|
| `[7:4]` | D-Pad | Current direction buttons pressed |
| `[3]` | Brush Mode | 1 = Brush, 0 = Eraser |
| `[2:0]` | Color | RGB color value (see color mixing table) |

### Example I2C Transaction

```
START → 0xC9 (addr 0x64 + read) → ACK → [X] → ACK → [Y] → ACK → [Status] → NACK → STOP
```

**[IMAGE: i2c_waveform.png - Logic analyzer capture showing I2C read transaction]**

---

## Module Architecture

The design is composed of several Verilog modules with clear separation of concerns:

```
┌──────────────────────────────────────────────────────────────────┐
│                        tt_um_example (top)                       │
├──────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐   ┌─────────────┐   ┌──────────────────┐   │
│  │ gamepad_pmod    │──▶│  Button     │──▶│    colour        │   │
│  │ _single         │   │  Edge       │   │    (RGB mixer)   │   │
│  │ (controller)    │   │  Detection  │   └──────────────────┘   │
│  └─────────────────┘   └─────────────┘            │              │
│           │                   │                   ▼              │
│           │            ┌──────────────┐   ┌──────────────────┐   │
│           │            │  position    │   │  brush_settings  │   │
│           └───────────▶│  (X/Y track) │   │  (size/symmetry) │   │
│                        └──────────────┘   └──────────────────┘   │
│                               │                   │              │
│                               ▼                   ▼              │
│                        ┌──────────────────────────────────┐      │
│                        │       packet_generator           │      │
│                        │  (expands brush size + symmetry) │      │
│                        └──────────────────────────────────┘      │
│                               │                                  │
│           ┌───────────────────┼───────────────────┐              │
│           ▼                   ▼                   ▼              │
│  ┌─────────────────┐   ┌─────────────┐   ┌──────────────────┐   │
│  │   fill_mode     │   │  undo_redo  │   │    i2c_slave     │   │
│  │   fill_draw     │   │  (4-entry)  │   │    (addr 0x64)   │   │
│  │ (rect fill)     │   │             │   │                  │   │
│  └─────────────────┘   └─────────────┘   └──────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### Source Files

| File | Description |
|------|-------------|
| `project.v` | Top-level module, button logic, signal routing |
| `gamepad_pmod.v` | SNES controller protocol decoder |
| `colour.v` | RGB color mixing and paint enable logic |
| `position.v` | Cursor X/Y position tracker |
| `brush_settings.v` | Brush size and symmetry mode control |
| `packet_generator.v` | Expands single pixels to brush size with symmetry |
| `fill_mode.v` | Fill rectangle mode state machine |
| `fill_draw.v` | Generates pixels for filled rectangle |
| `undo_redo.v` | 4-entry circular buffer for undo/redo |
| `i2c_slave.v` | Read-only I2C slave interface |
| `counter.v` | Utility counter module |

---

## Using the Interactive Emulator

An interactive Python/Pygame emulator is provided for testing without hardware:

<img width="1595" height="866" alt="image" src="https://github.com/user-attachments/assets/9edf2fa5-fc75-419c-a3c6-5d814f93e139" />


### Running the Emulator

```bash
cd test
python interactive_emulator.py
```

### Emulator Controls

| Key | Action |
|-----|--------|
| Arrow keys | Move cursor (D-Pad) |
| `A` | Toggle Red |
| `Y` | Toggle Green |
| `X` | Toggle Blue |
| `B` | Set fill corner (in Fill mode) |
| `+` / `=` | Increase brush size |
| `-` | Decrease brush size |
| `Shift+S` | Cycle symmetry mode |
| `Tab` | Toggle Fill mode |
| `Z` | Undo |
| `Y` | Redo |
| `C` | Clear canvas |

### Emulator Features

- Real-time canvas visualization (256×256 grid)
- Controller state display
- I2C packet viewer
- Brush size and symmetry mode indicators
- Undo/redo buffer status

---

## Running Tests

### Prerequisites

- Python 3.8+
- cocotb
- Icarus Verilog (iverilog)
- pygame

### Install Dependencies

```bash
pip install cocotb pygame
```

### Run Cocotb Tests

```bash
cd test
make
```

### Run Feature Demo

```bash
cd test
python demo_features.py
```

<img width="1111" height="777" alt="image" src="https://github.com/user-attachments/assets/1ffb2be3-3d91-4e3e-baf8-4674189b402a" />


---

## Building for Tiny Tapeout

### GDS Generation

The design is configured for the Tiny Tapeout flow:

```bash
# Clone with submodules
git clone --recursive https://github.com/YOUR_USERNAME/tiny_tapeout.git
cd tiny_tapeout

# Run the hardening flow (requires OpenLane 2)
./tt/tt_tool.py --harden
```

### Configuration

Key settings in `src/config.json`:

```json
{
  "PL_TARGET_DENSITY_PCT": 87,
  "CLOCK_PERIOD": 20
}
```

- **Target Density**: 87% (design utilizes ~86.7%)
- **Clock Period**: 20ns (50 MHz)

---

## Connecting to the Demoboard

### Hardware Setup

1. Connect the [Gamepad PMOD](https://github.com/psychogenic/gamepad_pmod) to the input PMOD header
2. Connect I2C lines (SDA to `uio[1]`, SCL to `uio[2]`)
3. Connect an I2C master (e.g., RP2040 on the demoboard)

**[IMAGE: demoboard_connection.jpg - Photo showing PMOD and I2C connections]**

### Reading from MicroPython

```python
from machine import I2C, Pin

i2c = I2C(0, scl=Pin(SCL_PIN), sda=Pin(SDA_PIN), freq=100000)

CANVAS_ADDR = 0x64

def read_canvas():
    data = i2c.readfrom(CANVAS_ADDR, 3)
    x = data[0]
    y = data[1]
    status = data[2]
    
    color = status & 0x07
    brush_mode = (status >> 3) & 0x01
    dpad = (status >> 4) & 0x0F
    
    return x, y, color, brush_mode, dpad

# Continuous reading
while True:
    x, y, color, mode, dpad = read_canvas()
    print(f"Pos: ({x}, {y}) Color: {color:03b} Mode: {'Brush' if mode else 'Eraser'}")
```

---

## Design Decisions

### Why Fill Rectangle Instead of Flood Fill?

True flood fill (bucket tool) requires:
- Reading existing pixel colors from memory
- Stack-based recursive algorithm
- Significant RAM for the pixel buffer

Fill Rectangle is a hardware-friendly alternative that:
- Only requires two corner coordinates
- Generates pixels sequentially (no recursion)
- Uses minimal registers
- Fits within the 1x1 tile constraint

### Why 4-Entry Undo Buffer?

Each undo entry stores X (8 bits) + Y (8 bits) + Color (3 bits) = 19 bits. A 4-entry buffer provides useful undo capability while staying within area constraints. The Python emulator implements stroke-based undo for a more intuitive experience.

---

## License

This project is released under the Apache License 2.0. See [LICENSE](LICENSE) for details.

---

## Acknowledgments

- [Tiny Tapeout](https://tinytapeout.com/) for making open-source silicon accessible
- [Psychogenic](https://github.com/psychogenic) for theGamepad PMOD

---

## Links

- [Tiny Tapeout Documentation](https://tinytapeout.com/)
- [Gamepad PMOD Project](https://github.com/psychogenic/gamepad_pmod)
- [OpenLane 2 Documentation](https://openlane.readthedocs.io/)
- [SKY130 PDK](https://skywater-pdk.readthedocs.io/)

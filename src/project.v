/*
 * Copyright (c) 2024 Your Name
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_example (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered
    input  wire       clk,      // system clock
    input  wire       rst_n     // reset_n - low to reset
);

    // ================================================================
    // Input Mapping - Gamepad PMOD
    // ================================================================
    // ui_in[0] = pmod_data   (serial data from gamepad)
    // ui_in[1] = pmod_clk    (serial clock from gamepad)
    // ui_in[2] = pmod_latch  (latch signal from gamepad)
    //
    // Controller Button Mapping:
    //   D-Pad (up/down/left/right) -> Cursor movement
    //   Y button -> Toggle Red
    //   X button -> Toggle Green
    //   B button -> Toggle Blue
    //   A button -> Toggle Brush/Eraser mode

    wire pmod_data  = ui_in[0];
    wire pmod_clk   = ui_in[1];
    wire pmod_latch = ui_in[2];


    // ================================================================
    // 1. Gamepad PMOD Interface
    // ================================================================
    // Instantiate the gamepad driver to decode controller button states
    wire gp_b, gp_y, gp_select, gp_start;
    wire gp_up, gp_down, gp_left, gp_right;
    wire gp_a, gp_x, gp_l, gp_r;
    wire gp_is_present;

    gamepad_pmod_single gamepad_inst (
        .rst_n      (rst_n),
        .clk        (clk),
        .pmod_data  (pmod_data),
        .pmod_clk   (pmod_clk),
        .pmod_latch (pmod_latch),
        .b          (gp_b),
        .y          (gp_y),
        .select     (gp_select),
        .start      (gp_start),
        .up         (gp_up),
        .down       (gp_down),
        .left       (gp_left),
        .right      (gp_right),
        .a          (gp_a),
        .x          (gp_x),
        .l          (gp_l),
        .r          (gp_r),
        .is_present (gp_is_present)
    );


    // ================================================================
    // 2. Button Toggle Logic
    // ================================================================
    // Gamepad buttons are momentary, so we need edge detection and
    // toggle registers for RGB colour selection and brush/eraser mode.
    //
    // Button assignments:
    //   Y -> Toggle Red
    //   X -> Toggle Green
    //   B -> Toggle Blue
    //   A -> Toggle Brush/Eraser (1 = Brush, 0 = Eraser)

    // Previous button state registers (for edge detection)
    reg y_prev, x_prev, b_prev, a_prev;

    // Toggle state registers
    reg sw_red, sw_green, sw_blue;
    reg brush_mode;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            // Reset previous button states
            y_prev <= 1'b0;
            x_prev <= 1'b0;
            b_prev <= 1'b0;
            a_prev <= 1'b0;
            // Reset toggle states (start in brush mode with no colour)
            sw_red     <= 1'b0;
            sw_green   <= 1'b0;
            sw_blue    <= 1'b0;
            brush_mode <= 1'b1;  // Start in brush mode
        end else begin
            // Store previous button states
            y_prev <= gp_y;
            x_prev <= gp_x;
            b_prev <= gp_b;
            a_prev <= gp_a;

            // Toggle Red on Y button rising edge
            if (gp_y && !y_prev)
                sw_red <= ~sw_red;

            // Toggle Green on X button rising edge
            if (gp_x && !x_prev)
                sw_green <= ~sw_green;

            // Toggle Blue on B button rising edge
            if (gp_b && !b_prev)
                sw_blue <= ~sw_blue;

            // Toggle Brush/Eraser on A button rising edge
            if (gp_a && !a_prev)
                brush_mode <= ~brush_mode;
        end
    end


    // ================================================================
    // 3. Position Tracker
    // ================================================================
    // Uses D-pad inputs from gamepad for cursor movement
    wire [7:0] x_pos;
    wire [7:0] y_pos;

    // Direction mapping: {UP, DOWN, LEFT, RIGHT}
    wire [3:0] dir_udlr = {gp_up, gp_down, gp_left, gp_right};

    position pos_inst (
        .x_pos   (x_pos),
        .y_pos   (y_pos),
        .dir_udlr(dir_udlr),
        .clk     (clk),
        .rst_n   (rst_n)
    );


    // ================================================================
    // 4. Colour Mixing Module
    // ================================================================
    // Combines RGB toggle states with brush/eraser mode to produce
    // the final colour output.
    //
    // Paint Enable Logic:
    //   - Brush mode + RGB=000: paint_enable=0 (move without painting)
    //   - Brush mode + RGB!=000: paint_enable=1 (paint the colour)
    //   - Eraser mode: paint_enable=1 (paint black to erase)
    wire [2:0] colour_out;
    wire paint_enable;

    colour colour_inst (
        .clk          (clk),
        .rst_n        (rst_n),
        .sw_red       (sw_red),
        .sw_green     (sw_green),
        .sw_blue      (sw_blue),
        .brush_mode   (brush_mode),
        .colour_out   (colour_out),
        .paint_enable (paint_enable)
    );


    // ================================================================
    // 5. Status Byte Construction
    // ================================================================
    // Status Byte [7:0]:
    //   [7]   = Up button (active state)
    //   [6]   = Down button (active state)
    //   [5]   = Left button (active state)
    //   [4]   = Right button (active state)
    //   [3]   = Brush/Eraser mode (1 = Brush, 0 = Eraser)
    //   [2:0] = RGB Colour (mixed output from colour module)
    wire [7:0] status_reg;

    assign status_reg[7]   = gp_up;
    assign status_reg[6]   = gp_down;
    assign status_reg[5]   = gp_left;
    assign status_reg[4]   = gp_right;
    assign status_reg[3]   = brush_mode;
    assign status_reg[2:0] = colour_out;


    // ================================================================
    // 6. I2C Slave Interface
    // ================================================================
    wire sda_oe_int;    // "output enable" for open-drain (1 = pull low)
    wire sda_out_int;   // not really needed (always 0 in your slave)

    i2c_slave #(
        .I2C_ADDR(7'b1100100)   // 0x64
    ) i2c_slave_inst (
        .scl    (uio_in[2]),    // SCL from pad
        .sda_in (uio_in[1]),    // SDA from pad
        .sda_oe (sda_oe_int),   // open-drain enable from slave
        .sda_out(sda_out_int),  // always 0 inside slave
        .i2c_state(uo_out[2:0]),
        .x_pos  (x_pos),
        .y_pos  (y_pos),
        .status (status_reg),
        .clk    (clk),
        .rst_n  (rst_n)
    );


    // ================================================================
    // 7. Open-drain Wiring on Chip Pads
    // ================================================================
    // SDA (uio[1]) is open-drain:
    //  - we ALWAYS drive 0 on the data line
    //  - we ONLY enable the driver when sda_oe_int = 1
    
    // SDA = uio[1]
    assign uio_out[1] = 1'b0;        // open-drain drives only 0
    assign uio_oe[1]  = sda_oe_int;  // 1 = pull low, 0 = release

    // SCL = uio[2]
    assign uio_out[2] = 1'b0;        // input only
    assign uio_oe[2]  = 1'b0;
    
    // All other uio pins unused
    assign uio_out[7:3] = 5'b0;
    assign uio_oe[7:3]  = 5'b0;
    assign uio_out[0]   = 1'b0;
    assign uio_oe[0]    = 1'b0;

    assign uo_out[7:3] = 5'b0;


    // ================================================================
    // Unused Signal Handling
    // ================================================================
    wire _unused = &{ena, 1'b0};
    wire _unused_sda_out = sda_out_int;
    wire _unused_ui = &{ui_in[7:3]};
    wire _unused_gp = &{gp_select, gp_start, gp_l, gp_r, gp_is_present};
    wire _unused_paint = paint_enable;  // Can be derived from status byte

endmodule

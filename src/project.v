/*
 * Tiny Canvas - MS Paint Style Drawing Tool
 * Gamepad-controlled pixel art with brush sizes, symmetry, fill, and undo.
 */

`default_nettype none

module tt_um_example (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);

    // ================================================================
    // Gamepad PMOD Input
    // ================================================================
    wire pmod_data  = ui_in[0];
    wire pmod_clk   = ui_in[1];
    wire pmod_latch = ui_in[2];

    wire gp_b, gp_y, gp_select, gp_start;
    wire gp_up, gp_down, gp_left, gp_right;
    wire gp_a, gp_x, gp_l, gp_r;
    wire gp_is_present;

    gamepad_pmod_single gamepad_inst (
        .rst_n(rst_n), .clk(clk),
        .pmod_data(pmod_data), .pmod_clk(pmod_clk), .pmod_latch(pmod_latch),
        .b(gp_b), .y(gp_y), .select(gp_select), .start(gp_start),
        .up(gp_up), .down(gp_down), .left(gp_left), .right(gp_right),
        .a(gp_a), .x(gp_x), .l(gp_l), .r(gp_r),
        .is_present(gp_is_present)
    );

    // ================================================================
    // Button Edge Detection & Toggle Logic
    // ================================================================
    reg y_prev, x_prev, b_prev;
    reg sw_red, sw_green, sw_blue, brush_mode;
    
    // Combo detection for undo/redo
    wire undo_combo = gp_l && gp_r;
    wire redo_combo = gp_select && gp_start;
    reg undo_prev, redo_prev;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            y_prev <= 1'b0; x_prev <= 1'b0; b_prev <= 1'b0;
            sw_red <= 1'b0; sw_green <= 1'b0; sw_blue <= 1'b0;
            brush_mode <= 1'b1;
            undo_prev <= 1'b0; redo_prev <= 1'b0;
        end else begin
            y_prev <= gp_y; x_prev <= gp_x; b_prev <= gp_b;
            undo_prev <= undo_combo; redo_prev <= redo_combo;
            
            if (gp_y && !y_prev) sw_red <= ~sw_red;
            if (gp_x && !x_prev) sw_green <= ~sw_green;
            if (gp_b && !b_prev) sw_blue <= ~sw_blue;
        end
    end
    
    wire undo_trigger = undo_combo && !undo_prev;
    wire redo_trigger = redo_combo && !redo_prev;

    // ================================================================
    // Position Tracker
    // ================================================================
    wire [7:0] x_pos, y_pos;
    wire [3:0] dir_udlr = {gp_up, gp_down, gp_left, gp_right};
    wire movement = gp_up || gp_down || gp_left || gp_right;
    reg movement_prev;
    wire movement_edge = movement && !movement_prev;
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) movement_prev <= 1'b0;
        else movement_prev <= movement;
    end

    position pos_inst (
        .x_pos(x_pos), .y_pos(y_pos),
        .dir_udlr(dir_udlr),
        .clk(clk), .rst_n(rst_n)
    );

    // ================================================================
    // Colour Mixing
    // ================================================================
    wire [2:0] colour_out;
    wire paint_enable;

    colour colour_inst (
        .clk(clk), .rst_n(rst_n),
        .sw_red(sw_red), .sw_green(sw_green), .sw_blue(sw_blue),
        .brush_mode(brush_mode),
        .colour_out(colour_out),
        .paint_enable(paint_enable)
    );

    // ================================================================
    // Brush Settings (L/R = size, Start = symmetry)
    // ================================================================
    wire [2:0] brush_size;
    wire [1:0] symmetry_mode;

    brush_settings brush_inst (
        .clk(clk), .rst_n(rst_n),
        .btn_size_up(gp_r),
        .btn_size_down(gp_l),
        .btn_symmetry(gp_start),
        .brush_size(brush_size),
        .symmetry_mode(symmetry_mode)
    );

    // ================================================================
    // Fill Mode (Select = toggle, A = set corner)
    // ================================================================
    wire fill_active;
    wire [7:0] corner_a_x, corner_a_y, corner_b_x, corner_b_y;
    wire corner_a_set, fill_trigger;

    fill_mode fill_mode_inst (
        .clk(clk), .rst_n(rst_n),
        .btn_mode(gp_select),
        .btn_point(gp_a),
        .x_pos(x_pos), .y_pos(y_pos),
        .fill_active(fill_active),
        .corner_a_x(corner_a_x), .corner_a_y(corner_a_y),
        .corner_a_set(corner_a_set),
        .corner_b_x(corner_b_x), .corner_b_y(corner_b_y),
        .fill_trigger(fill_trigger)
    );

    // ================================================================
    // Fill Drawing (filled rectangle)
    // ================================================================
    wire [7:0] fill_x, fill_y;
    wire fill_valid, fill_busy, fill_done;

    fill_draw fill_draw_inst (
        .clk(clk), .rst_n(rst_n),
        .start(fill_trigger),
        .x0(corner_a_x), .y0(corner_a_y),
        .x1(corner_b_x), .y1(corner_b_y),
        .x_out(fill_x), .y_out(fill_y),
        .pixel_valid(fill_valid),
        .busy(fill_busy),
        .done(fill_done)
    );

    // ================================================================
    // Pixel Source Selection
    // ================================================================
    // Freehand: when moving and paint enabled and not in fill mode
    wire freehand_trigger = movement_edge && paint_enable && !fill_active;
    
    // Select pixel source: fill operation or cursor position
    wire [7:0] pixel_x = fill_busy ? fill_x : x_pos;
    wire [7:0] pixel_y = fill_busy ? fill_y : y_pos;
    wire pixel_trigger = freehand_trigger || fill_valid;

    // ================================================================
    // Packet Generator (expands brush size + symmetry)
    // ================================================================
    wire [7:0] pkt_x, pkt_y;
    wire pkt_valid, pkt_busy;

    packet_generator pkt_inst (
        .clk(clk), .rst_n(rst_n),
        .trigger(pixel_trigger),
        .x_in(pixel_x), .y_in(pixel_y),
        .brush_size(brush_size),
        .symmetry_mode(symmetry_mode),
        .x_out(pkt_x), .y_out(pkt_y),
        .valid(pkt_valid),
        .busy(pkt_busy)
    );

    // ================================================================
    // Undo/Redo Buffer
    // ================================================================
    wire [7:0] undo_x, undo_y;
    wire [2:0] undo_color;
    wire undo_restore, can_undo, can_redo;

    undo_redo undo_inst (
        .clk(clk), .rst_n(rst_n),
        .save(pkt_valid),
        .undo(undo_trigger),
        .redo(redo_trigger),
        .x_in(pkt_x), .y_in(pkt_y),
        .color_in(colour_out),
        .x_out(undo_x), .y_out(undo_y),
        .color_out(undo_color),
        .restore_valid(undo_restore),
        .can_undo(can_undo),
        .can_redo(can_redo)
    );

    // ================================================================
    // Status Byte Construction
    // ================================================================
    wire [7:0] status_reg;
    assign status_reg[7]   = gp_up;
    assign status_reg[6]   = gp_down;
    assign status_reg[5]   = gp_left;
    assign status_reg[4]   = gp_right;
    assign status_reg[3]   = brush_mode;
    assign status_reg[2:0] = colour_out;

    // ================================================================
    // I2C Slave Interface
    // ================================================================
    wire sda_oe_int, sda_out_int;

    i2c_slave #(.I2C_ADDR(7'b1100100)) i2c_slave_inst (
        .scl(uio_in[2]),
        .sda_in(uio_in[1]),
        .sda_oe(sda_oe_int),
        .sda_out(sda_out_int),
        .i2c_state(uo_out[2:0]),
        .x_pos(pkt_x),
        .y_pos(pkt_y),
        .status(status_reg),
        .clk(clk),
        .rst_n(rst_n)
    );

    // ================================================================
    // I/O Wiring
    // ================================================================
    assign uio_out[1] = 1'b0;
    assign uio_oe[1]  = sda_oe_int;
    assign uio_out[2] = 1'b0;
    assign uio_oe[2]  = 1'b0;
    assign uio_out[7:3] = 5'b0;
    assign uio_oe[7:3]  = 5'b0;
    assign uio_out[0]   = 1'b0;
    assign uio_oe[0]    = 1'b0;
    assign uo_out[7:3] = 5'b0;

    // ================================================================
    // Unused Signals
    // ================================================================
    wire _unused = &{ena, sda_out_int, ui_in[7:3], uio_in[7:3], uio_in[0],
                     gp_is_present, pkt_busy, fill_busy, fill_done, corner_a_set,
                     undo_restore, undo_x, undo_y, undo_color, can_undo, can_redo};

endmodule

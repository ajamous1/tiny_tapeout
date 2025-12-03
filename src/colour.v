// ============================================================================
// Colour Mixing Module
// Combines RGB switch inputs to produce a 3-bit colour output.
//
// Colour Mixing Logic:
//   - R only      -> Red     (3'b100)
//   - G only      -> Green   (3'b010)
//   - B only      -> Blue    (3'b001)
//   - R + G       -> Yellow  (3'b110)
//   - R + B       -> Magenta (3'b101)
//   - G + B       -> Cyan    (3'b011)
//   - R + G + B   -> White   (3'b111)
//   - None        -> Black   (3'b000)
//
// Paint Enable Logic:
//   - Brush mode + RGB=000: paint_enable = 0 (don't paint, just move)
//   - Brush mode + RGB!=000: paint_enable = 1 (paint the colour)
//   - Eraser mode: paint_enable = 1 (paint black to erase)
//
// This allows moving over the canvas without accidentally painting
// when no colour is selected in brush mode.
// ============================================================================

module colour (
    input  wire        clk,
    input  wire        rst_n,

    // RGB switch inputs (directly from ui_in)
    input  wire        sw_red,
    input  wire        sw_green,
    input  wire        sw_blue,
    
    // Brush/Eraser mode (1 = Brush, 0 = Eraser)
    input  wire        brush_mode,

    // 3-bit colour output [2:0] = {R, G, B}
    output reg  [2:0]  colour_out,
    
    // Paint enable: 1 = paint the pixel, 0 = don't modify pixel
    output reg         paint_enable
);

    // ----------------------------------------------------------------
    // Colour Mixing Logic
    // RGB switches are combined directly when in brush mode.
    // In eraser mode, always output black (000).
    // ----------------------------------------------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            // Default to black on reset, no painting
            colour_out   <= 3'b000;
            paint_enable <= 1'b0;
        end else begin
            if (brush_mode) begin
                // Brush mode: combine RGB switches directly
                // colour_out[2] = Red
                // colour_out[1] = Green
                // colour_out[0] = Blue
                colour_out <= {sw_red, sw_green, sw_blue};
                
                // Only enable painting if at least one colour is selected
                // RGB=000 means "don't paint, just move"
                paint_enable <= (sw_red | sw_green | sw_blue);
            end else begin
                // Eraser mode: always black, always paint (to erase)
                colour_out   <= 3'b000;
                paint_enable <= 1'b1;
            end
        end
    end

endmodule

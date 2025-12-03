// Brush size and symmetry settings.
// Size: 0-7 (maps to 1x1 through 8x8)
// Symmetry: 0=off, 1=horizontal, 2=vertical, 3=4-way

module brush_settings (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       btn_size_up,
    input  wire       btn_size_down,
    input  wire       btn_symmetry,
    output reg  [2:0] brush_size,
    output reg  [1:0] symmetry_mode
);

    reg btn_up_prev, btn_down_prev, btn_sym_prev;
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            brush_size <= 3'd0;
            symmetry_mode <= 2'd0;
            btn_up_prev <= 1'b0;
            btn_down_prev <= 1'b0;
            btn_sym_prev <= 1'b0;
        end else begin
            btn_up_prev <= btn_size_up;
            btn_down_prev <= btn_size_down;
            btn_sym_prev <= btn_symmetry;
            
            // Size up on rising edge (R button alone)
            if (btn_size_up && !btn_up_prev && !btn_size_down)
                if (brush_size < 3'd7)
                    brush_size <= brush_size + 1;
            
            // Size down on rising edge (L button alone)
            if (btn_size_down && !btn_down_prev && !btn_size_up)
                if (brush_size > 3'd0)
                    brush_size <= brush_size - 1;
            
            // Cycle symmetry on rising edge (Start button)
            if (btn_symmetry && !btn_sym_prev)
                symmetry_mode <= symmetry_mode + 1;
        end
    end

endmodule

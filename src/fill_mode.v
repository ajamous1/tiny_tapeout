// Fill mode controller.
// Select button toggles fill mode on/off.
// A button sets corners for filled rectangle.

module fill_mode (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       btn_mode,      // Toggle fill mode (Select)
    input  wire       btn_point,     // Set corner (A button)
    input  wire [7:0] x_pos,
    input  wire [7:0] y_pos,
    output reg        fill_active,   // Fill mode is on
    output reg  [7:0] corner_a_x,
    output reg  [7:0] corner_a_y,
    output reg        corner_a_set,
    output reg  [7:0] corner_b_x,
    output reg  [7:0] corner_b_y,
    output reg        fill_trigger   // Start fill operation
);

    reg btn_mode_prev, btn_point_prev;
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            fill_active <= 1'b0;
            corner_a_x <= 8'd0;
            corner_a_y <= 8'd0;
            corner_a_set <= 1'b0;
            corner_b_x <= 8'd0;
            corner_b_y <= 8'd0;
            fill_trigger <= 1'b0;
            btn_mode_prev <= 1'b0;
            btn_point_prev <= 1'b0;
        end else begin
            btn_mode_prev <= btn_mode;
            btn_point_prev <= btn_point;
            fill_trigger <= 1'b0;
            
            // Toggle fill mode
            if (btn_mode && !btn_mode_prev) begin
                fill_active <= ~fill_active;
                corner_a_set <= 1'b0;  // Reset on mode change
            end
            
            // Set corners (only when fill mode active)
            if (btn_point && !btn_point_prev && fill_active) begin
                if (!corner_a_set) begin
                    corner_a_x <= x_pos;
                    corner_a_y <= y_pos;
                    corner_a_set <= 1'b1;
                end else begin
                    corner_b_x <= x_pos;
                    corner_b_y <= y_pos;
                    fill_trigger <= 1'b1;
                    corner_a_set <= 1'b0;
                end
            end
        end
    end

endmodule


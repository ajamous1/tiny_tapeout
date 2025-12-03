// Draw mode controller.
// Modes: 0=freehand, 1=line, 2=rectangle, 3=spray
// Handles point setting for line/rectangle modes.

module draw_mode (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       btn_mode,      // Cycles through modes
    input  wire       btn_point,     // Sets point A or B
    input  wire [7:0] x_pos,
    input  wire [7:0] y_pos,
    output reg  [1:0] mode,
    output reg  [7:0] point_a_x,
    output reg  [7:0] point_a_y,
    output reg        point_a_valid,
    output reg  [7:0] point_b_x,
    output reg  [7:0] point_b_y,
    output reg        shape_trigger
);

    reg btn_mode_prev, btn_point_prev;
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            mode <= 2'd0;
            point_a_x <= 0; point_a_y <= 0;
            point_b_x <= 0; point_b_y <= 0;
            point_a_valid <= 1'b0;
            shape_trigger <= 1'b0;
            btn_mode_prev <= 1'b0;
            btn_point_prev <= 1'b0;
        end else begin
            btn_mode_prev <= btn_mode;
            btn_point_prev <= btn_point;
            shape_trigger <= 1'b0;
            
            // Cycle mode on rising edge
            if (btn_mode && !btn_mode_prev) begin
                mode <= mode + 1;
                point_a_valid <= 1'b0;  // Reset point on mode change
            end
            
            // Set point on rising edge (only in line/rect modes)
            if (btn_point && !btn_point_prev && (mode == 2'd1 || mode == 2'd2)) begin
                if (!point_a_valid) begin
                    point_a_x <= x_pos;
                    point_a_y <= y_pos;
                    point_a_valid <= 1'b1;
                end else begin
                    point_b_x <= x_pos;
                    point_b_y <= y_pos;
                    shape_trigger <= 1'b1;
                    point_a_valid <= 1'b0;
                end
            end
        end
    end

endmodule

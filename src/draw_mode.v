// Draw mode controller.
// Modes: 0=Freehand, 1=Rectangle, 2=Line

module draw_mode (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       btn_mode,
    input  wire       btn_point,
    input  wire [7:0] x_pos,
    input  wire [7:0] y_pos,
    output reg  [1:0] mode,
    output reg  [7:0] point_a_x,
    output reg  [7:0] point_a_y,
    output reg        point_a_set,
    output reg  [7:0] point_b_x,
    output reg  [7:0] point_b_y,
    output reg        shape_trigger
);

    reg btn_mode_prev, btn_point_prev;
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            mode <= 2'd0;
            point_a_x <= 8'd0; point_a_y <= 8'd0;
            point_b_x <= 8'd0; point_b_y <= 8'd0;
            point_a_set <= 1'b0;
            shape_trigger <= 1'b0;
            btn_mode_prev <= 1'b0;
            btn_point_prev <= 1'b0;
        end else begin
            btn_mode_prev <= btn_mode;
            btn_point_prev <= btn_point;
            shape_trigger <= 1'b0;
            
            // Cycle mode (0 -> 1 -> 2 -> 0)
            if (btn_mode && !btn_mode_prev) begin
                if (mode == 2'd2)
                    mode <= 2'd0;
                else
                    mode <= mode + 2'd1;
                point_a_set <= 1'b0;
            end
            
            // Set point (only in shape modes)
            if (btn_point && !btn_point_prev && mode != 2'd0) begin
                if (!point_a_set) begin
                    point_a_x <= x_pos;
                    point_a_y <= y_pos;
                    point_a_set <= 1'b1;
                end else begin
                    point_b_x <= x_pos;
                    point_b_y <= y_pos;
                    shape_trigger <= 1'b1;
                    point_a_set <= 1'b0;
                end
            end
        end
    end

endmodule

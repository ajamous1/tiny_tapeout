// Simple shape drawing - circle and rectangle outlines.
// Outputs pixels one at a time.

module shape_draw (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       start,
    input  wire [1:0] shape,         // 0=none, 1=rect, 2=circle, 3=line
    input  wire [7:0] x0, y0,        // Point A
    input  wire [7:0] x1, y1,        // Point B
    output reg  [7:0] x_out,
    output reg  [7:0] y_out,
    output reg        pixel_valid,
    output reg        busy,
    output reg        done
);

    reg [7:0] min_x, max_x, min_y, max_y;
    reg [7:0] cx, cy, r;             // Circle center and radius
    reg [7:0] curr_x, curr_y;
    reg [3:0] state;
    reg [7:0] angle;                 // For circle (0-255 = 0-360 degrees)
    
    localparam IDLE = 4'd0, SETUP = 4'd1;
    localparam RECT_TOP = 4'd2, RECT_RIGHT = 4'd3, RECT_BOT = 4'd4, RECT_LEFT = 4'd5;
    localparam CIRCLE = 4'd6;
    localparam LINE = 4'd7;
    localparam FINISH = 4'd8;
    
    // Simple approximations for circle (8 points around)
    wire [7:0] sin_approx [0:7];
    wire [7:0] cos_approx [0:7];
    
    // Precomputed sin/cos * 127 for 8 angles (0, 45, 90, 135, 180, 225, 270, 315)
    assign sin_approx[0] = 8'd0;    assign cos_approx[0] = 8'd127;  // 0
    assign sin_approx[1] = 8'd90;   assign cos_approx[1] = 8'd90;   // 45
    assign sin_approx[2] = 8'd127;  assign cos_approx[2] = 8'd0;    // 90
    assign sin_approx[3] = 8'd90;   assign cos_approx[3] = 8'd166;  // 135 (cos is -90, stored as 256-90)
    assign sin_approx[4] = 8'd0;    assign cos_approx[4] = 8'd129;  // 180 (cos is -127)
    assign sin_approx[5] = 8'd166;  assign cos_approx[5] = 8'd166;  // 225
    assign sin_approx[6] = 8'd129;  assign cos_approx[6] = 8'd0;    // 270 (sin is -127)
    assign sin_approx[7] = 8'd166;  assign cos_approx[7] = 8'd90;   // 315
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            busy <= 1'b0;
            done <= 1'b0;
            pixel_valid <= 1'b0;
            curr_x <= 8'd0; curr_y <= 8'd0;
            min_x <= 8'd0; max_x <= 8'd0; min_y <= 8'd0; max_y <= 8'd0;
            cx <= 8'd0; cy <= 8'd0; r <= 8'd0;
            angle <= 8'd0;
            x_out <= 8'd0; y_out <= 8'd0;
        end else begin
            pixel_valid <= 1'b0;
            done <= 1'b0;
            
            case (state)
                IDLE: begin
                    busy <= 1'b0;
                    if (start && shape != 2'd0) begin
                        busy <= 1'b1;
                        state <= SETUP;
                    end
                end
                
                SETUP: begin
                    // Calculate bounds
                    min_x <= (x0 < x1) ? x0 : x1;
                    max_x <= (x0 < x1) ? x1 : x0;
                    min_y <= (y0 < y1) ? y0 : y1;
                    max_y <= (y0 < y1) ? y1 : y0;
                    
                    // Circle: center and radius
                    cx <= (x0 + x1) >> 1;
                    cy <= (y0 + y1) >> 1;
                    r <= ((x0 > x1 ? x0 - x1 : x1 - x0) + (y0 > y1 ? y0 - y1 : y1 - y0)) >> 2;
                    
                    curr_x <= (x0 < x1) ? x0 : x1;
                    curr_y <= (y0 < y1) ? y1 : y0;  // Start at top-left
                    angle <= 8'd0;
                    
                    case (shape)
                        2'd1: state <= RECT_TOP;
                        2'd2: state <= CIRCLE;
                        2'd3: state <= LINE;
                        default: state <= FINISH;
                    endcase
                end
                
                // Rectangle: draw 4 edges
                RECT_TOP: begin
                    x_out <= curr_x;
                    y_out <= max_y;
                    pixel_valid <= 1'b1;
                    if (curr_x >= max_x) begin
                        curr_y <= max_y - 8'd1;
                        state <= RECT_RIGHT;
                    end else
                        curr_x <= curr_x + 8'd1;
                end
                
                RECT_RIGHT: begin
                    x_out <= max_x;
                    y_out <= curr_y;
                    pixel_valid <= 1'b1;
                    if (curr_y <= min_y) begin
                        curr_x <= max_x - 8'd1;
                        state <= RECT_BOT;
                    end else
                        curr_y <= curr_y - 8'd1;
                end
                
                RECT_BOT: begin
                    x_out <= curr_x;
                    y_out <= min_y;
                    pixel_valid <= 1'b1;
                    if (curr_x <= min_x) begin
                        curr_y <= min_y + 8'd1;
                        state <= RECT_LEFT;
                    end else
                        curr_x <= curr_x - 8'd1;
                end
                
                RECT_LEFT: begin
                    if (curr_y >= max_y)
                        state <= FINISH;
                    else begin
                        x_out <= min_x;
                        y_out <= curr_y;
                        pixel_valid <= 1'b1;
                        curr_y <= curr_y + 8'd1;
                    end
                end
                
                // Circle: 32 points around circumference
                CIRCLE: begin
                    // Simple 8-point circle using symmetry
                    case (angle[4:2])
                        3'd0: begin x_out <= cx + r; y_out <= cy; end
                        3'd1: begin x_out <= cx + ((r * 8'd90) >> 7); y_out <= cy + ((r * 8'd90) >> 7); end
                        3'd2: begin x_out <= cx; y_out <= cy + r; end
                        3'd3: begin x_out <= cx - ((r * 8'd90) >> 7); y_out <= cy + ((r * 8'd90) >> 7); end
                        3'd4: begin x_out <= cx - r; y_out <= cy; end
                        3'd5: begin x_out <= cx - ((r * 8'd90) >> 7); y_out <= cy - ((r * 8'd90) >> 7); end
                        3'd6: begin x_out <= cx; y_out <= cy - r; end
                        3'd7: begin x_out <= cx + ((r * 8'd90) >> 7); y_out <= cy - ((r * 8'd90) >> 7); end
                    endcase
                    pixel_valid <= 1'b1;
                    
                    if (angle >= 8'd248)
                        state <= FINISH;
                    else
                        angle <= angle + 8'd8;
                end
                
                // Line: step from A to B
                LINE: begin
                    x_out <= curr_x;
                    y_out <= curr_y;
                    pixel_valid <= 1'b1;
                    
                    if (curr_x == x1 && curr_y == y1)
                        state <= FINISH;
                    else begin
                        if (curr_x < x1) curr_x <= curr_x + 8'd1;
                        else if (curr_x > x1) curr_x <= curr_x - 8'd1;
                        
                        if (curr_y < y1) curr_y <= curr_y + 8'd1;
                        else if (curr_y > y1) curr_y <= curr_y - 8'd1;
                    end
                end
                
                FINISH: begin
                    done <= 1'b1;
                    busy <= 1'b0;
                    state <= IDLE;
                end
                
                default: state <= IDLE;
            endcase
        end
    end

endmodule


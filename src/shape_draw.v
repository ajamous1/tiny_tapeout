// Simple shape drawing - rectangle and line only.

module shape_draw (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       start,
    input  wire [1:0] shape,         // 0=none, 1=rect, 2=line
    input  wire [7:0] x0, y0,
    input  wire [7:0] x1, y1,
    output reg  [7:0] x_out,
    output reg  [7:0] y_out,
    output reg        pixel_valid,
    output reg        busy,
    output reg        done
);

    reg [7:0] min_x, max_x, min_y, max_y;
    reg [7:0] curr_x, curr_y;
    reg [2:0] state;
    
    localparam IDLE = 3'd0, SETUP = 3'd1;
    localparam RECT_TOP = 3'd2, RECT_RIGHT = 3'd3, RECT_BOT = 3'd4, RECT_LEFT = 3'd5;
    localparam LINE = 3'd6, FINISH = 3'd7;
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            busy <= 1'b0;
            done <= 1'b0;
            pixel_valid <= 1'b0;
            curr_x <= 8'd0; curr_y <= 8'd0;
            min_x <= 8'd0; max_x <= 8'd0; min_y <= 8'd0; max_y <= 8'd0;
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
                    min_x <= (x0 < x1) ? x0 : x1;
                    max_x <= (x0 < x1) ? x1 : x0;
                    min_y <= (y0 < y1) ? y0 : y1;
                    max_y <= (y0 < y1) ? y1 : y0;
                    curr_x <= (x0 < x1) ? x0 : x1;
                    curr_y <= (y0 < y1) ? y1 : y0;
                    
                    if (shape == 2'd1)
                        state <= RECT_TOP;
                    else
                        state <= LINE;
                end
                
                // Rectangle edges
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
                
                // Line: step from start to end
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

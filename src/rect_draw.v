// Simple rectangle outline drawing module.
// Draws four edges of a rectangle given two corners.

module rect_draw (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       start,
    input  wire [7:0] x0, y0,    // Corner A
    input  wire [7:0] x1, y1,    // Corner B
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
    localparam TOP = 3'd2, RIGHT = 3'd3, BOTTOM = 3'd4, LEFT = 3'd5;
    localparam FINISH = 3'd6;
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            busy <= 1'b0;
            done <= 1'b0;
            pixel_valid <= 1'b0;
            min_x <= 0; max_x <= 0; min_y <= 0; max_y <= 0;
            curr_x <= 0; curr_y <= 0;
            x_out <= 0; y_out <= 0;
        end else begin
            pixel_valid <= 1'b0;
            done <= 1'b0;
            
            case (state)
                IDLE: begin
                    busy <= 1'b0;
                    if (start) begin
                        busy <= 1'b1;
                        state <= SETUP;
                    end
                end
                
                SETUP: begin
                    // Find min/max coordinates
                    min_x <= (x0 < x1) ? x0 : x1;
                    max_x <= (x0 < x1) ? x1 : x0;
                    min_y <= (y0 < y1) ? y0 : y1;
                    max_y <= (y0 < y1) ? y1 : y0;
                    curr_x <= (x0 < x1) ? x0 : x1;
                    state <= TOP;
                end
                
                TOP: begin  // Draw top edge (y = max_y)
                    x_out <= curr_x;
                    y_out <= max_y;
                    pixel_valid <= 1'b1;
                    if (curr_x >= max_x) begin
                        curr_y <= max_y - 1;
                        state <= RIGHT;
                    end else
                        curr_x <= curr_x + 1;
                end
                
                RIGHT: begin  // Draw right edge (x = max_x)
                    x_out <= max_x;
                    y_out <= curr_y;
                    pixel_valid <= 1'b1;
                    if (curr_y <= min_y) begin
                        curr_x <= max_x - 1;
                        state <= BOTTOM;
                    end else
                        curr_y <= curr_y - 1;
                end
                
                BOTTOM: begin  // Draw bottom edge (y = min_y)
                    x_out <= curr_x;
                    y_out <= min_y;
                    pixel_valid <= 1'b1;
                    if (curr_x <= min_x) begin
                        curr_y <= min_y + 1;
                        state <= LEFT;
                    end else
                        curr_x <= curr_x - 1;
                end
                
                LEFT: begin  // Draw left edge (x = min_x)
                    if (curr_y >= max_y)
                        state <= FINISH;
                    else begin
                        x_out <= min_x;
                        y_out <= curr_y;
                        pixel_valid <= 1'b1;
                        curr_y <= curr_y + 1;
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

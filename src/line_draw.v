// Simple line drawing module.
// Draws from point A to point B by stepping one pixel at a time.
// Uses diagonal movement when possible, then straight.

module line_draw (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       start,
    input  wire [7:0] x0, y0,    // Start point
    input  wire [7:0] x1, y1,    // End point
    output reg  [7:0] x_out,
    output reg  [7:0] y_out,
    output reg        pixel_valid,
    output reg        busy,
    output reg        done
);

    reg [7:0] curr_x, curr_y;
    reg [7:0] end_x, end_y;
    reg [1:0] state;
    
    localparam IDLE = 2'd0, DRAW = 2'd1, FINISH = 2'd2;
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            busy <= 1'b0;
            done <= 1'b0;
            pixel_valid <= 1'b0;
            curr_x <= 0; curr_y <= 0;
            end_x <= 0; end_y <= 0;
            x_out <= 0; y_out <= 0;
        end else begin
            pixel_valid <= 1'b0;
            done <= 1'b0;
            
            case (state)
                IDLE: begin
                    busy <= 1'b0;
                    if (start) begin
                        curr_x <= x0;
                        curr_y <= y0;
                        end_x <= x1;
                        end_y <= y1;
                        busy <= 1'b1;
                        state <= DRAW;
                    end
                end
                
                DRAW: begin
                    // Output current pixel
                    x_out <= curr_x;
                    y_out <= curr_y;
                    pixel_valid <= 1'b1;
                    
                    // Check if done
                    if (curr_x == end_x && curr_y == end_y) begin
                        state <= FINISH;
                    end else begin
                        // Step towards target
                        if (curr_x < end_x)
                            curr_x <= curr_x + 1;
                        else if (curr_x > end_x)
                            curr_x <= curr_x - 1;
                        
                        if (curr_y < end_y)
                            curr_y <= curr_y + 1;
                        else if (curr_y > end_y)
                            curr_y <= curr_y - 1;
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

// Filled rectangle drawing.
// Outputs every pixel in a rectangular region, row by row.

module fill_draw (
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
    reg [1:0] state;
    
    localparam IDLE = 2'd0, SETUP = 2'd1, FILL = 2'd2, FINISH = 2'd3;
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            busy <= 1'b0;
            done <= 1'b0;
            pixel_valid <= 1'b0;
            min_x <= 8'd0; max_x <= 8'd0;
            min_y <= 8'd0; max_y <= 8'd0;
            curr_x <= 8'd0; curr_y <= 8'd0;
            x_out <= 8'd0; y_out <= 8'd0;
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
                    // Calculate bounds
                    min_x <= (x0 < x1) ? x0 : x1;
                    max_x <= (x0 < x1) ? x1 : x0;
                    min_y <= (y0 < y1) ? y0 : y1;
                    max_y <= (y0 < y1) ? y1 : y0;
                    curr_x <= (x0 < x1) ? x0 : x1;
                    curr_y <= (y0 < y1) ? y0 : y1;
                    state <= FILL;
                end
                
                FILL: begin
                    // Output current pixel
                    x_out <= curr_x;
                    y_out <= curr_y;
                    pixel_valid <= 1'b1;
                    
                    // Advance to next pixel
                    if (curr_x < max_x) begin
                        curr_x <= curr_x + 8'd1;
                    end else if (curr_y < max_y) begin
                        curr_x <= min_x;
                        curr_y <= curr_y + 8'd1;
                    end else begin
                        state <= FINISH;
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


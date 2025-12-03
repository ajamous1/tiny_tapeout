// Expands a single pixel into multiple pixels based on brush size and symmetry.
// Outputs pixels one at a time for I2C transmission.

module packet_generator (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       trigger,
    input  wire [7:0] x_in,
    input  wire [7:0] y_in,
    input  wire [2:0] brush_size,     // 0=1x1, 1=2x2, etc.
    input  wire [1:0] symmetry_mode,  // 0=off, 1=H, 2=V, 3=4-way
    output reg  [7:0] x_out,
    output reg  [7:0] y_out,
    output reg        valid,
    output reg        busy
);

    reg [3:0] bx, by;     // Brush offset counters
    reg [1:0] sym;        // Symmetry index
    reg [7:0] base_x, base_y;
    reg [3:0] size;       // 4-bit to match bx/by width
    reg [1:0] state;
    
    localparam IDLE = 2'd0, CALC = 2'd1, OUTPUT = 2'd2, NEXT = 2'd3;
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            busy <= 1'b0;
            valid <= 1'b0;
            bx <= 4'd0; by <= 4'd0; sym <= 2'd0;
            base_x <= 8'd0; base_y <= 8'd0; size <= 4'd0;
            x_out <= 8'd0; y_out <= 8'd0;
        end else begin
            valid <= 1'b0;
            
            case (state)
                IDLE: begin
                    busy <= 1'b0;
                    if (trigger) begin
                        busy <= 1'b1;
                        base_x <= x_in;
                        base_y <= y_in;
                        size <= {1'b0, brush_size};  // Extend to 4 bits
                        bx <= 4'd0; by <= 4'd0; sym <= 2'd0;
                        state <= CALC;
                    end
                end
                
                CALC: begin
                    // Calculate pixel position with brush offset
                    x_out <= base_x + {4'd0, bx} - {5'd0, size[3:1]};
                    y_out <= base_y + {4'd0, by} - {5'd0, size[3:1]};
                    state <= OUTPUT;
                end
                
                OUTPUT: begin
                    // Apply symmetry and output
                    case (sym)
                        2'd0: begin  // Original
                            valid <= 1'b1;
                        end
                        2'd1: begin  // H-mirror or V-mirror
                            if (symmetry_mode == 2'd1)
                                x_out <= 8'd255 - x_out;
                            else
                                y_out <= 8'd255 - y_out;
                            valid <= 1'b1;
                        end
                        2'd2: begin  // H-mirror (for 4-way)
                            x_out <= 8'd255 - x_out;
                            valid <= 1'b1;
                        end
                        2'd3: begin  // Both mirrors (for 4-way)
                            x_out <= 8'd255 - x_out;
                            y_out <= 8'd255 - y_out;
                            valid <= 1'b1;
                        end
                    endcase
                    state <= NEXT;
                end
                
                NEXT: begin
                    // Next symmetry position?
                    if (symmetry_mode > 2'd0 && sym < (symmetry_mode == 2'd3 ? 2'd3 : 2'd1)) begin
                        sym <= sym + 2'd1;
                        state <= CALC;
                    end
                    // Next brush pixel?
                    else if (bx < size) begin
                        bx <= bx + 4'd1;
                        sym <= 2'd0;
                        state <= CALC;
                    end
                    else if (by < size) begin
                        bx <= 4'd0;
                        by <= by + 4'd1;
                        sym <= 2'd0;
                        state <= CALC;
                    end
                    else begin
                        state <= IDLE;
                    end
                end
                
                default: state <= IDLE;
            endcase
        end
    end

endmodule

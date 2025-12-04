// Tracks an 8-bit X,Y position on a 256×256 grid.
// Movement wraps around at edges.
// EDGE-TRIGGERED: Position only updates on rising edge of direction signals

module position (
    output reg [7:0] x_pos,
    output reg [7:0] y_pos,
    input  wire [3:0] dir_udlr, // {UP, DOWN, LEFT, RIGHT}
    input  wire clk,
    input  wire rst_n
);

// Edge detection - store previous state of direction signals
reg [3:0] dir_prev;

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        x_pos <= 8'd0;
        y_pos <= 8'd0;
        dir_prev <= 4'b0000;
    end
    else begin
        // Store previous state for edge detection
        dir_prev <= dir_udlr;
        
        // Only move on RISING EDGE of direction signals
        // (0,0) is bottom-left corner (math coordinates)
        
        // RIGHT: dir_udlr[3] rising edge
        if (dir_udlr[3] && !dir_prev[3])
            x_pos <= x_pos + 1;
        // LEFT: dir_udlr[2] rising edge
        else if (dir_udlr[2] && !dir_prev[2])
            x_pos <= x_pos - 1;
        // DOWN: dir_udlr[1] rising edge (decreases y)
        else if (dir_udlr[1] && !dir_prev[1])
            y_pos <= y_pos - 1;
        // UP: dir_udlr[0] rising edge (increases y)
        else if (dir_udlr[0] && !dir_prev[0])
            y_pos <= y_pos + 1;
    end
end

endmodule

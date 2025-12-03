// Simple 8-bit random number generator.
// Uses shift register with XOR feedback for pseudo-random sequence.

module lfsr (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       enable,
    output wire [7:0] random
);

    reg [7:0] lfsr_reg;
    
    // Feedback: XOR bits 7, 5, 4, 3 (standard 8-bit LFSR taps)
    wire feedback = lfsr_reg[7] ^ lfsr_reg[5] ^ lfsr_reg[4] ^ lfsr_reg[3];
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            lfsr_reg <= 8'hA5;  // Non-zero seed
        else if (enable)
            lfsr_reg <= {lfsr_reg[6:0], feedback};
    end
    
    assign random = lfsr_reg;

endmodule

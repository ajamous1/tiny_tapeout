// Simple 8-level undo/redo buffer.
// Stores position and color for each operation.

module undo_redo (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       save,          // Save current state
    input  wire       undo,          // Undo last operation
    input  wire       redo,          // Redo undone operation
    input  wire [7:0] x_in,
    input  wire [7:0] y_in,
    input  wire [2:0] color_in,
    output reg  [7:0] x_out,
    output reg  [7:0] y_out,
    output reg  [2:0] color_out,
    output reg        restore_valid,
    output wire       can_undo,
    output wire       can_redo
);

    // Buffer: 8 entries of {x, y, color} = 8 x 19 bits
    reg [7:0] buf_x [0:7];
    reg [7:0] buf_y [0:7];
    reg [2:0] buf_c [0:7];
    
    reg [2:0] write_ptr;
    reg [3:0] count;
    reg [3:0] redo_avail;
    
    reg save_prev, undo_prev, redo_prev;
    
    assign can_undo = (count > redo_avail);
    assign can_redo = (redo_avail > 0);
    
    integer i;
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            write_ptr <= 0;
            count <= 0;
            redo_avail <= 0;
            restore_valid <= 1'b0;
            save_prev <= 0; undo_prev <= 0; redo_prev <= 0;
            x_out <= 0; y_out <= 0; color_out <= 0;
            for (i = 0; i < 8; i = i + 1) begin
                buf_x[i] <= 0; buf_y[i] <= 0; buf_c[i] <= 0;
            end
        end else begin
            save_prev <= save;
            undo_prev <= undo;
            redo_prev <= redo;
            restore_valid <= 1'b0;
            
            // Save on rising edge
            if (save && !save_prev) begin
                buf_x[write_ptr] <= x_in;
                buf_y[write_ptr] <= y_in;
                buf_c[write_ptr] <= color_in;
                write_ptr <= write_ptr + 1;
                if (count < 8) count <= count + 1;
                redo_avail <= 0;  // Clear redo on new save
            end
            
            // Undo on rising edge
            if (undo && !undo_prev && can_undo) begin
                redo_avail <= redo_avail + 1;
                x_out <= buf_x[(write_ptr - redo_avail - 1) & 3'b111];
                y_out <= buf_y[(write_ptr - redo_avail - 1) & 3'b111];
                color_out <= buf_c[(write_ptr - redo_avail - 1) & 3'b111];
                restore_valid <= 1'b1;
            end
            
            // Redo on rising edge
            if (redo && !redo_prev && can_redo) begin
                redo_avail <= redo_avail - 1;
                x_out <= buf_x[(write_ptr - redo_avail) & 3'b111];
                y_out <= buf_y[(write_ptr - redo_avail) & 3'b111];
                color_out <= buf_c[(write_ptr - redo_avail) & 3'b111];
                restore_valid <= 1'b1;
            end
        end
    end

endmodule

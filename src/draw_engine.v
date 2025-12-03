// Coordinates drawing operations across modes.
// Routes pixel output from different drawing modules.

module draw_engine (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [1:0] mode,           // 0=free, 1=line, 2=rect, 3=spray
    input  wire [7:0] x_pos,
    input  wire [7:0] y_pos,
    input  wire       move_trigger,   // Cursor moved
    input  wire       shape_trigger,  // Shape points set
    input  wire [7:0] point_a_x,
    input  wire [7:0] point_a_y,
    input  wire [7:0] point_b_x,
    input  wire [7:0] point_b_y,
    input  wire       paint_enable,
    output reg  [7:0] pixel_x,
    output reg  [7:0] pixel_y,
    output reg        pixel_valid,
    output wire       busy
);

    // Line drawing module
    wire line_valid, line_busy, line_done;
    wire [7:0] line_x, line_y;
    reg line_start;
    
    line_draw line_inst (
        .clk(clk), .rst_n(rst_n),
        .start(line_start),
        .x0(point_a_x), .y0(point_a_y),
        .x1(point_b_x), .y1(point_b_y),
        .x_out(line_x), .y_out(line_y),
        .pixel_valid(line_valid),
        .busy(line_busy), .done(line_done)
    );
    
    // Rectangle drawing module
    wire rect_valid, rect_busy, rect_done;
    wire [7:0] rect_x, rect_y;
    reg rect_start;
    
    rect_draw rect_inst (
        .clk(clk), .rst_n(rst_n),
        .start(rect_start),
        .x0(point_a_x), .y0(point_a_y),
        .x1(point_b_x), .y1(point_b_y),
        .x_out(rect_x), .y_out(rect_y),
        .pixel_valid(rect_valid),
        .busy(rect_busy), .done(rect_done)
    );
    
    // LFSR for spray mode
    wire [7:0] random;
    reg lfsr_en;
    
    lfsr lfsr_inst (
        .clk(clk), .rst_n(rst_n),
        .enable(lfsr_en),
        .random(random)
    );
    
    assign busy = line_busy || rect_busy;
    
    reg move_prev, shape_prev;
    reg [2:0] spray_cnt;
    reg [1:0] state;
    
    localparam IDLE = 2'd0, SPRAY = 2'd1, LINE = 2'd2, RECT = 2'd3;
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            pixel_valid <= 1'b0;
            line_start <= 1'b0;
            rect_start <= 1'b0;
            lfsr_en <= 1'b0;
            move_prev <= 1'b0;
            shape_prev <= 1'b0;
            spray_cnt <= 0;
            pixel_x <= 0; pixel_y <= 0;
        end else begin
            pixel_valid <= 1'b0;
            line_start <= 1'b0;
            rect_start <= 1'b0;
            lfsr_en <= 1'b0;
            move_prev <= move_trigger;
            shape_prev <= shape_trigger;
            
            case (state)
                IDLE: begin
                    // Shape trigger for line/rect
                    if (shape_trigger && !shape_prev) begin
                        if (mode == 2'd1) begin
                            line_start <= 1'b1;
                            state <= LINE;
                        end else if (mode == 2'd2) begin
                            rect_start <= 1'b1;
                            state <= RECT;
                        end
                    end
                    // Movement trigger
                    else if (move_trigger && !move_prev && paint_enable) begin
                        if (mode == 2'd0) begin  // Freehand
                            pixel_x <= x_pos;
                            pixel_y <= y_pos;
                            pixel_valid <= 1'b1;
                        end else if (mode == 2'd3) begin  // Spray
                            spray_cnt <= 3'd4;
                            state <= SPRAY;
                        end
                    end
                end
                
                SPRAY: begin
                    lfsr_en <= 1'b1;
                    pixel_x <= x_pos + random[3:0] - 4'd8;
                    pixel_y <= y_pos + random[7:4] - 4'd8;
                    pixel_valid <= 1'b1;
                    if (spray_cnt > 1)
                        spray_cnt <= spray_cnt - 1;
                    else
                        state <= IDLE;
                end
                
                LINE: begin
                    if (line_valid) begin
                        pixel_x <= line_x;
                        pixel_y <= line_y;
                        pixel_valid <= 1'b1;
                    end
                    if (line_done) state <= IDLE;
                end
                
                RECT: begin
                    if (rect_valid) begin
                        pixel_x <= rect_x;
                        pixel_y <= rect_y;
                        pixel_valid <= 1'b1;
                    end
                    if (rect_done) state <= IDLE;
                end
                
                default: state <= IDLE;
            endcase
        end
    end

endmodule

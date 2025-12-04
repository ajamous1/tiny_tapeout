// ============================================================================
// Simple I2C Slave (Read-Only)
// Responds to address match with 4 sequential bytes: x_pos, y_pos, status, brush_status
//
// Implements:
//   - START/STOP detection
//   - 7-bit address decode
//   - ACK generation
//   - MSB-first transmit byte engine
//   - Master ACK (MACK) handling
//   - Multi-byte read sequencing
//
// Open-drain SDA interface:
//   sda_oe = 1 → pull SDA low
//   sda_oe = 0 → release SDA (float high through pull-up)
// ============================================================================
// ============================================================================
// Simple I2C Slave (Read-Only)  — WITH DEBUG PRINTS
// ============================================================================

module i2c_slave #(
    parameter I2C_ADDR = 7'b1100100   // 0x64
)(
    input  wire       scl,
    input  wire       sda_in,
    output wire       sda_oe,
    output wire       sda_out,
    output wire [2:0] i2c_state,
    input  wire [7:0] x_pos,
    input  wire [7:0] y_pos,
    input  wire [7:0] status,
    input  wire [7:0] brush_status,   // 4th byte: fill, symmetry, brush size
    input  wire       clk,
    input  wire       rst_n
);


    // ------------------------------
    // SDA open-drain
    // ------------------------------
    reg pull_sda;
    assign sda_out = 1'b0;
    assign sda_oe  = pull_sda;

    // ------------------------------
    // Sync
    // ------------------------------
    reg [3:0] scl_d = 0;
    reg [3:0] sda_d = 0;

    always @(posedge clk) begin
        scl_d <= {scl_d[2:0], scl};
        sda_d <= {sda_d[2:0], sda_in};
    end

    wire scl_rise = (scl_d == 4'b0111);
    wire scl_fall = (scl_d == 4'b1000);
    //wire sda_rise = (sda_d == 4'b0111);
    wire sda_fall = (sda_d == 4'b1000);

    wire scl_high = scl_d[3];
    wire scl_low  = ~scl_d[3];


    // ------------------------------
    // START/STOP detect
    // ------------------------------
    reg bus_start;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            bus_start <= 1'b0;
        end else begin
            bus_start <= sda_fall && scl_high;

            // if (sda_fall && scl_high)
            //     $display("[%0t] I2C: START detected", $time);
        end
    end

    // ------------------------------
    // FSM
    // ------------------------------
    typedef enum logic [2:0] {
        IDLE       = 3'd0,
        ADDR_SHIFT = 3'd1,
        ACK_ADDR   = 3'd2,
        TX_BYTE    = 3'd3,
        MACK       = 3'd4,
        NEXT_BYTE  = 3'd5
    } state_t;

    state_t state;

    // internal regs
    reg [7:0] shreg;
    reg [3:0] bit_counter;
    reg       address_match;
    reg       read_check;
    reg [1:0] byte_index;
    //reg [7:0] addr_rw;
    reg       ack_asserted;


    // ------------------------------
    // Main FSM
    // ------------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state         <= IDLE;
            shreg         <= 0;
            pull_sda      <= 0;
            bit_counter   <= 0;
            address_match <= 0;
            read_check    <= 0;
            byte_index    <= 0;
           // addr_rw       <= 0;

        end else begin

            case (state)

            

            // --------------------------------------------------------------
            // IDLE
            // --------------------------------------------------------------
            IDLE: begin
                pull_sda <= 1'b0;

                if (bus_start) begin
                    // $display("[%0t] FSM: → ADDR_SHIFT", $time);
                    state       <= ADDR_SHIFT;
                    bit_counter <= 0;
                end
            end

            // --------------------------------------------------------------
            // ADDR_SHIFT — shift in address byte
            // --------------------------------------------------------------
            ADDR_SHIFT: begin
                if (scl_rise) begin

                    shreg <= {shreg[6:0], sda_in};
                    bit_counter <= bit_counter + 1;

                    // $display("[%0t] ADDR_SHIFT: bit %0d = %0b (shreg=%b)",
                    //          $time, bit_counter, sda_in, {shreg[6:0], sda_in});

                    if (bit_counter == 7) begin
                        //addr_rw       <= {shreg[6:0], sda_in};
                        address_match <= ( {shreg[6:0], sda_in} >> 1 ) == {1'b0, I2C_ADDR};
                        read_check    <= sda_in;
                        bit_counter <= 0;
                        ack_asserted <= 0;
                        state <= ACK_ADDR;

                        // $display("[%0t] ADDR byte received = %b", 
                        //          $time, {shreg[6:0], sda_in});
                        // $display("[%0t] Address match? %0d (expected %b)",
                        //         $time,
                        //         (({shreg[6:0], sda_in} >> 1) == I2C_ADDR),
                        //         I2C_ADDR);
                        // $display("[%0t] R/W = %0d", $time, sda_in);
                    end
                end
            end

            // --------------------------------------------------------------
            // ACK_ADDR
            // --------------------------------------------------------------
            ACK_ADDR: begin
                if (address_match) begin
                    if (scl_low && !ack_asserted) begin
                        //$display("[%0t] pulling SDA sig high", $time);
                        pull_sda <= 1'b1;  // ACK
                        ack_asserted <= 1;
                    end

                    // wait for end of clock cycle to release ACK
                    if (scl_fall && ack_asserted) begin
                        //$display("[%0t] releasing sda", $time);
                        pull_sda <= 1'b0;
                        ack_asserted <= 0;

                        if (read_check) begin
                            // $display("[%0t] FSM: → TX_BYTE (sending x_pos=%0d)", 
                            //          $time, x_pos);
                            shreg <= x_pos;
                            byte_index <= 0;  // Reset byte index for new transaction
                            state <= TX_BYTE;
                        end else begin
                            // $display("[%0t] ERROR: Write not supported → IDLE", $time);
                            // state <= IDLE;
                        end
                    end
                end else begin
                    //$display("[%0t] NACK: Address mismatch", $time);
                    state <= IDLE;
                end
            end

            // --------------------------------------------------------------
            // TX_BYTE
            // --------------------------------------------------------------
            TX_BYTE: begin
                if (scl_low)
                    pull_sda <= (shreg[7] == 1'b0);

                if (scl_rise) begin
                    // $display("[%0t] TX_BYTE: sending bit %0d = %0b",
                    //          $time, bit_counter, shreg[7]);

                    shreg <= {shreg[6:0], 1'b0};
                    bit_counter <= bit_counter + 1;
                end
                if (scl_fall && bit_counter == 8) begin
                        // $display("[%0t] TX_BYTE: finished byte", $time);
                        bit_counter <= 0;
                        pull_sda <= 0;
                        state <= MACK;
                    end
            end

            // --------------------------------------------------------------
            // MACK
            // --------------------------------------------------------------
            MACK: begin
                if (scl_rise) begin
                    // $display("[%0t] MACK: master sent %s",
                    //          $time, (sda_in == 0 ? "ACK" : "NACK"));

                    if (sda_in == 0)
                        state <= NEXT_BYTE;
                    else
                        state <= IDLE;
                end
            end

            // --------------------------------------------------------------
            // NEXT_BYTE - Now sends 4 bytes: x_pos, y_pos, status, brush_status
            // --------------------------------------------------------------
            NEXT_BYTE: begin
                case (byte_index)
                    0: begin
                        //$display("[%0t] NEXT: Sending y_pos=%0d", $time, y_pos);
                        shreg      <= y_pos;
                        byte_index <= 1;
                        state      <= TX_BYTE;
                    end
                    1: begin
                        //$display("[%0t] NEXT: Sending status=%0d", $time, status);
                        shreg      <= status;
                        byte_index <= 2;
                        state      <= TX_BYTE;
                    end
                    2: begin
                        //$display("[%0t] NEXT: Sending brush_status=%0d", $time, brush_status);
                        shreg      <= brush_status;
                        byte_index <= 3;
                        state      <= TX_BYTE;
                    end
                    default: begin
                        //$display("[%0t] NEXT: Done (all bytes sent)", $time);
                        byte_index <= 0;
                        state      <= IDLE;
                    end
                endcase
            end

            default: begin
                state <= IDLE;
            end

            endcase
        end
    end

    assign i2c_state = state;

endmodule

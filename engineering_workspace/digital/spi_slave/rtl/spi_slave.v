`timescale 1ns / 1ps

module spi_slave (

    input  wire       clk,
    input  wire       rst_n,

    // SPI interface
    input  wire       spi_cs_n,
    input  wire       spi_sck,
    input  wire       spi_mosi,
    output reg        spi_miso,

    // Register write interface
    output reg        wr_en,
    output reg [6:0]  wr_addr,
    output reg [7:0]  wr_data,

    // Register read interface
    output reg [6:0]  rd_addr,
    input  wire [7:0] rd_data

);

    // =====================================================
    // SPI INPUT SYNCHRONIZERS
    // =====================================================

    reg [2:0] sck_sync;
    reg [2:0] cs_sync;
    reg [1:0] mosi_sync;

    wire sck_rise;
    wire sck_fall;
    wire cs_active;

    // FIXED 2026-11-14. Was sck_sync[1:0].
    // sck_sync[0] is the flop that samples the asynchronous spi_sck
    // directly, so it can be metastable. Edge-detecting on [1:0]
    // made the result depend on that unresolved value, which slips
    // or duplicates a bit and corrupts the address or data byte.
    // [1] and [2] are both post-second-flop and clean, so detect
    // there. cs_sync already did this correctly via ~cs_sync[2];
    // mosi_sync[1] is correct too. SCK was the odd one out, which
    // is why verilator reported sck_sync[2] as unused.
    //
    // Cost: one extra clk of latency, 20 ns. SCK is capped near
    // 5 MHz (100 ns half period) by the oversampling requirement,
    // so this is immaterial.
    //
    // Simulation CANNOT show the original bug -- an event simulator
    // has no metastability -- so the 26 passing tests never covered
    // it.
    assign sck_rise = (sck_sync[2:1] == 2'b01);
    assign sck_fall = (sck_sync[2:1] == 2'b10);

    assign cs_active = ~cs_sync[2];

    // =====================================================
    // INTERNAL REGISTERS
    // =====================================================

    reg [4:0] bit_count;

    reg [7:0] rx_shift;
    reg [7:0] tx_shift;

    reg       rw;
    reg [6:0] address;

    // =====================================================
    // SYNCHRONIZATION
    // =====================================================

    always @(posedge clk or negedge rst_n) begin

        if (!rst_n) begin

            sck_sync  <= 3'b000;
            cs_sync   <= 3'b111;
            mosi_sync <= 2'b00;

        end else begin

            sck_sync <= {
                sck_sync[1:0],
                spi_sck
            };

            cs_sync <= {
                cs_sync[1:0],
                spi_cs_n
            };

            mosi_sync <= {
                mosi_sync[0],
                spi_mosi
            };

        end

    end

    // =====================================================
    // SPI TRANSACTION CONTROLLER
    // =====================================================

    always @(posedge clk or negedge rst_n) begin

        if (!rst_n) begin

            bit_count <= 5'd0;

            rx_shift <= 8'd0;
            tx_shift <= 8'd0;

            rw      <= 1'b0;
            address <= 7'd0;

            wr_en   <= 1'b0;
            wr_addr <= 7'd0;
            wr_data <= 8'd0;

            rd_addr <= 7'd0;

            spi_miso <= 1'b0;

        end else begin

            wr_en <= 1'b0;

            // CS inactive
            if (!cs_active) begin

                bit_count <= 5'd0;
                rx_shift <= 8'd0;

                spi_miso <= 1'b0;

            end else begin

                // =========================================
                // RISING EDGE: RECEIVE MOSI
                // =========================================

                if (sck_rise) begin

                    if (bit_count < 8) begin

                        rx_shift <= {
                            rx_shift[6:0],
                            mosi_sync[1]
                        };

                        if (bit_count == 7) begin

                            rw <= rx_shift[6];

                            address <= {
                                rx_shift[5:0],
                                mosi_sync[1]
                            };

                            rd_addr <= {
                                rx_shift[5:0],
                                mosi_sync[1]
                            };

                        end

                    end else if (bit_count < 16) begin

                        rx_shift <= {
                            rx_shift[6:0],
                            mosi_sync[1]
                        };

                        if (bit_count == 15) begin

                            if (!rw) begin

                                wr_en <= 1'b1;

                                wr_addr <= address;

                                wr_data <= {
                                    rx_shift[6:0],
                                    mosi_sync[1]
                                };

                            end

                        end

                    end

                    if (bit_count < 16)
                        bit_count <= bit_count + 1'b1;

                end

                // =========================================
                // FALLING EDGE: TRANSMIT MISO
                // =========================================

                if (sck_fall) begin

                    if (bit_count == 8) begin

                        tx_shift <= rd_data;

                        spi_miso <= rd_data[7];

                    end else if (
                        bit_count > 8 &&
                        bit_count < 16
                    ) begin

                        spi_miso <= tx_shift[6];

                        tx_shift <= {
                            tx_shift[6:0],
                            1'b0
                        };

                    end

                end

            end

        end

    end

endmodule

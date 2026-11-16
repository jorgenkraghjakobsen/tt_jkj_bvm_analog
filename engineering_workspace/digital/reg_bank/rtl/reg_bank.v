`timescale 1ns / 1ps

// ============================================================
// reg_bank.v
// Register bank for SKY130 Tiny Tapeout analog/digital IC
//
// Verilog-2001
// ASIC technology-independent RTL
// ============================================================

module reg_bank (

    input wire clk,
    input wire rst_n,

    // SPI register interface
    input wire       wr_en,
    input wire [6:0] wr_addr,
    input wire [7:0] wr_data,

    input wire [6:0] rd_addr,
    output reg [7:0] rd_data,

    // Bandgap status inputs
    input wire bg_ok,
    input wire bg_valid,

    // ========================================================
    // BANDGAP CONTROL
    // ========================================================

    output reg       bg_en,
    output reg [3:0] bg_trim,

    // ========================================================
    // BIAS GENERATOR CONTROL
    // ========================================================

    output reg       bias_en,
    output reg [4:0] bias_trim,

    // ========================================================
    // CLOCK DOUBLER CONTROL
    // ========================================================

    output reg dbl_en,

    // ========================================================
    // PWM 0 CONTROL
    // ========================================================

    output reg [7:0] pwm0_duty,
    output reg       pwm0_en,
    output reg       pwm0_width,
    output reg       pwm0_clk_sel,

    // ========================================================
    // PWM 1 CONTROL
    // ========================================================

    output reg [7:0] pwm1_duty,
    output reg       pwm1_en,
    output reg       pwm1_width,
    output reg       pwm1_clk_sel,

    // ========================================================
    // BANDGAP SEQUENCER CONTROL
    // ========================================================

    output reg [2:0] bg_div_sel,
    output reg       bg_burst,
    output reg [3:0] bg_hold_exp

);

    // ========================================================
    // REGISTER ADDRESSES
    // ========================================================

    localparam ADDR_BG_CTRL    = 7'h00;
    localparam ADDR_BIAS_CTRL  = 7'h01;
    localparam ADDR_CLK_CTRL   = 7'h02;

    localparam ADDR_PWM0_DUTY  = 7'h03;
    localparam ADDR_PWM0_CTRL  = 7'h04;

    localparam ADDR_PWM1_DUTY  = 7'h05;
    localparam ADDR_PWM1_CTRL  = 7'h06;

    localparam ADDR_STATUS     = 7'h07;
    localparam ADDR_BG_SEQ     = 7'h08;

    // ========================================================
    // WRITE REGISTER LOGIC
    // ========================================================

    always @(posedge clk or negedge rst_n) begin

        if (!rst_n) begin

            // Bandgap
            bg_en       <= 1'b1;
            bg_trim     <= 4'd8;

            // Bias generator
            bias_en     <= 1'b1;
            bias_trim   <= 5'd16;

            // Clock
            dbl_en      <= 1'b0;

            // PWM 0
            pwm0_duty   <= 8'h80;
            pwm0_en     <= 1'b1;
            pwm0_width  <= 1'b0;
            pwm0_clk_sel <= 1'b0;

            // PWM 1
            pwm1_duty   <= 8'h80;
            pwm1_en     <= 1'b1;
            pwm1_width  <= 1'b0;
            pwm1_clk_sel <= 1'b0;

            // Bandgap sequencer
            bg_div_sel  <= 3'd4;
            bg_burst    <= 1'b0;
            bg_hold_exp <= 4'd0;

        end

        else if (wr_en) begin

            case (wr_addr)

                // BG_CTRL
                ADDR_BG_CTRL: begin
                    bg_en   <= wr_data[7];
                    bg_trim <= wr_data[3:0];
                end

                // BIAS_CTRL
                ADDR_BIAS_CTRL: begin
                    bias_en   <= wr_data[7];
                    bias_trim <= wr_data[4:0];
                end

                // CLK_CTRL
                ADDR_CLK_CTRL: begin
                    dbl_en <= wr_data[0];
                end

                // PWM0_DUTY
                ADDR_PWM0_DUTY: begin
                    pwm0_duty <= wr_data;
                end

                // PWM0_CTRL
                ADDR_PWM0_CTRL: begin
                    pwm0_en      <= wr_data[0];
                    pwm0_width   <= wr_data[1];
                    pwm0_clk_sel <= wr_data[2];
                end

                // PWM1_DUTY
                ADDR_PWM1_DUTY: begin
                    pwm1_duty <= wr_data;
                end

                // PWM1_CTRL
                ADDR_PWM1_CTRL: begin
                    pwm1_en      <= wr_data[0];
                    pwm1_width   <= wr_data[1];
                    pwm1_clk_sel <= wr_data[2];
                end

                // BG_SEQ
                // bit[2:0] = div_sel
                // bit[3]   = burst
                // bit[7:4] = hold_exp
                ADDR_BG_SEQ: begin
                    bg_div_sel  <= wr_data[2:0];
                    bg_burst    <= wr_data[3];
                    bg_hold_exp <= wr_data[7:4];
                end

                // STATUS is read-only
                default: begin
                    // No write operation
                end

            endcase

        end

    end

    // ========================================================
    // READ REGISTER LOGIC
    // ========================================================

    always @(*) begin

        rd_data = 8'h00;

        case (rd_addr)

            ADDR_BG_CTRL: begin
                rd_data = {bg_en, 3'b000, bg_trim};
            end

            ADDR_BIAS_CTRL: begin
                rd_data = {bias_en, 2'b00, bias_trim};
            end

            ADDR_CLK_CTRL: begin
                rd_data = {7'b0000000, dbl_en};
            end

            ADDR_PWM0_DUTY: begin
                rd_data = pwm0_duty;
            end

            ADDR_PWM0_CTRL: begin
                rd_data = {5'b00000, pwm0_clk_sel,
                           pwm0_width, pwm0_en};
            end

            ADDR_PWM1_DUTY: begin
                rd_data = pwm1_duty;
            end

            ADDR_PWM1_CTRL: begin
                rd_data = {5'b00000, pwm1_clk_sel,
                           pwm1_width, pwm1_en};
            end

            // STATUS:
            // bit[0] = combined bg_ok
            // bit[1] = sequencer bg_valid
            ADDR_STATUS: begin
                rd_data = {6'b000000, bg_valid, bg_ok};
            end

            // BG_SEQ
            ADDR_BG_SEQ: begin
                rd_data = {bg_hold_exp, bg_burst, bg_div_sel};
            end

            default: begin
                rd_data = 8'h00;
            end

        endcase

    end

endmodule

`timescale 1ns / 1ps

// ============================================================
// dig_top.v
// Digital top-level macro
//
// SKY130 Tiny Tapeout mixed-signal IC
// Verilog-2001
//
// Includes:
//   1. SPI slave
//   2. Register bank
//   3. PWM0 and PWM1
//   4. Bandgap phase sequencer
//   5. Analog status synchronization
//
// Clock: 50 MHz
// Reset: Active-low
// ============================================================

module dig_top (

    input wire clk,
    input wire rst_n,
    input wire ena,

    // --------------------------------------------------------
    // SPI INTERFACE
    // --------------------------------------------------------

    input  wire spi_cs_n,
    input  wire spi_sck,
    input  wire spi_mosi,
    output wire spi_miso,

    // --------------------------------------------------------
    // ANALOG STATUS INPUT
    // --------------------------------------------------------

    input wire bias_ok,

    // --------------------------------------------------------
    // PWM CLOCK INPUTS
    // --------------------------------------------------------

    input wire pwm0_clk,
    input wire pwm1_clk,

    // --------------------------------------------------------
    // PWM OUTPUTS
    // --------------------------------------------------------

    output wire pwm0_out,
    output wire pwm1_out,

    // --------------------------------------------------------
    // BANDGAP CONTROL OUTPUTS
    // --------------------------------------------------------

    output wire       bg_en,
    output wire [3:0] bg_trim,

    // --------------------------------------------------------
    // BIAS GENERATOR CONTROL OUTPUTS
    // --------------------------------------------------------

    output wire       bias_en,
    output wire [4:0] bias_trim,

    // --------------------------------------------------------
    // CLOCK DOUBLER CONTROL
    // --------------------------------------------------------

    output wire dbl_en,

    // --------------------------------------------------------
    // PWM CLOCK SELECTION
    // --------------------------------------------------------

    output wire pwm0_clk_sel,
    output wire pwm1_clk_sel,

    // --------------------------------------------------------
    // BANDGAP SEQUENCER OUTPUTS
    // Connect these to analog/bandgap
    // --------------------------------------------------------

    output wire phi1,
    output wire phi2,
    output wire cap,
    output wire ota_en,
    output wire i8_en,

    // --------------------------------------------------------
    // BANDGAP STATUS
    // --------------------------------------------------------

    output wire bg_valid,
    output wire bg_ok_combined

);

    // ========================================================
    // INTERNAL SPI REGISTER INTERFACE
    // ========================================================

    wire       wr_en;
    wire [6:0] wr_addr;
    wire [7:0] wr_data;

    wire [6:0] rd_addr;
    wire [7:0] rd_data;

    // ========================================================
    // INTERNAL PWM CONFIGURATION
    // ========================================================

    wire [7:0] pwm0_duty;
    wire       pwm0_enable;
    wire       pwm0_width;

    wire [7:0] pwm1_duty;
    wire       pwm1_enable;
    wire       pwm1_width;

    // ========================================================
    // INTERNAL BANDGAP SEQUENCER CONFIGURATION
    // ========================================================

    wire [2:0] bg_div_sel;
    wire       bg_burst;
    wire [3:0] bg_hold_exp;

    // ========================================================
    // ANALOG STATUS SYNCHRONIZER
    // bias_ok crosses from analog circuitry into digital clock
    // domain. Use a two-stage synchronizer.
    // ========================================================

    reg bias_ok_meta;
    reg bias_ok_sync;

    always @(posedge clk or negedge rst_n) begin

        if (!rst_n) begin
            bias_ok_meta <= 1'b0;
            bias_ok_sync <= 1'b0;
        end

        else begin
            bias_ok_meta <= bias_ok;
            bias_ok_sync <= bias_ok_meta;
        end

    end

    // ========================================================
    // BANDGAP READY STATUS
    // ========================================================

    assign bg_ok_combined = bias_ok_sync & bg_valid;

    // ========================================================
    // SPI SLAVE
    // ========================================================

    spi_slave u_spi_slave (

        .clk       (clk),
        .rst_n     (rst_n),

        .spi_cs_n  (spi_cs_n),
        .spi_sck   (spi_sck),
        .spi_mosi  (spi_mosi),
        .spi_miso  (spi_miso),

        .wr_en     (wr_en),
        .wr_addr   (wr_addr),
        .wr_data   (wr_data),

        .rd_addr   (rd_addr),
        .rd_data   (rd_data)

    );

    // ========================================================
    // REGISTER BANK
    // ========================================================

    reg_bank u_reg_bank (

        .clk          (clk),
        .rst_n        (rst_n),

        .wr_en        (wr_en),
        .wr_addr      (wr_addr),
        .wr_data      (wr_data),

        .rd_addr      (rd_addr),
        .rd_data      (rd_data),

        // Status
        .bg_ok        (bg_ok_combined),
        .bg_valid     (bg_valid),

        // Bandgap
        .bg_en        (bg_en),
        .bg_trim      (bg_trim),

        // Bias
        .bias_en      (bias_en),
        .bias_trim    (bias_trim),

        // Clock doubler
        .dbl_en       (dbl_en),

        // PWM0
        .pwm0_duty    (pwm0_duty),
        .pwm0_en      (pwm0_enable),
        .pwm0_width   (pwm0_width),
        .pwm0_clk_sel (pwm0_clk_sel),

        // PWM1
        .pwm1_duty    (pwm1_duty),
        .pwm1_en      (pwm1_enable),
        .pwm1_width   (pwm1_width),
        .pwm1_clk_sel (pwm1_clk_sel),

        // Bandgap sequencer
        .bg_div_sel   (bg_div_sel),
        .bg_burst     (bg_burst),
        .bg_hold_exp  (bg_hold_exp)

    );

    // ========================================================
    // BANDGAP SEQUENCER
    // ========================================================

    bg_seq u_bg_seq (

        .clk       (clk),
        .rst_n     (rst_n),

        .en        (bg_en & ena),

        .div_sel   (bg_div_sel),
        .burst     (bg_burst),
        .hold_exp  (bg_hold_exp),

        .phi1      (phi1),
        .phi2      (phi2),
        .cap       (cap),
        .ota_en    (ota_en),
        .i8_en     (i8_en),
        .valid     (bg_valid)

    );

    // ========================================================
    // PWM 0
    // ========================================================

    pwm u_pwm0 (

        .clk       (pwm0_clk),
        .rst_n     (rst_n & ena),

        .enable    (pwm0_enable & ena),
        .width_sel (pwm0_width),
        .duty      (pwm0_duty),

        .pwm_out   (pwm0_out)

    );

    // ========================================================
    // PWM 1
    // ========================================================

    pwm u_pwm1 (

        .clk       (pwm1_clk),
        .rst_n     (rst_n & ena),

        .enable    (pwm1_enable & ena),
        .width_sel (pwm1_width),
        .duty      (pwm1_duty),

        .pwm_out   (pwm1_out)

    );

endmodule

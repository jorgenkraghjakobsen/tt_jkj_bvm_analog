/*
 * tt_um_bvm_mixed_signal_tile.v
 *
 * Tiny Tapeout wrapper for the BVM mixed-signal tile (TTSKY26d).
 *
 * ============================================================
 * REV 2, 2026-11-14. Port list verified against the real template:
 *   github.com/TinyTapeout/ttsky-analog-template  (src/project.v)
 *
 * Rev 1 was written from guesswork and had four mismatches, every
 * one of which would have failed the build:
 *   1. ua was [2:0]; the template declares [7:0]
 *   2. the 1.8 V rail was named VPWR; it is VDPWR
 *   3. power pins were wrapped in `ifdef USE_POWER_PINS; the
 *      template declares them unconditionally, as plain inputs
 *   4. the body instantiated dig_top while info.yaml listed only
 *      project.v, so dig_top was an unresolved module
 *
 * WHY THE BODY IS EMPTY
 * This is a custom-GDS submission. The gds workflow passes
 *     verilog_path: src/project.v
 * to TinyTapeout/tt-gds-action/custom_gds, which uses this file
 * ONLY to blackbox the macro for top-level integration. The actual
 * circuit is whatever is in gds/tt_um_bvm_mixed_signal_tile.gds.
 * The template's own project.v has an empty body for exactly this
 * reason. Putting RTL here would not change the silicon and would
 * oblige you to add every source file to info.yaml.
 *
 * CONSEQUENCE FOR LAYOUT -- do not skip this
 * Because there is no RTL here to tie things off, the tie-offs
 * become a LAYOUT requirement. The analog spec says no digital
 * output pin may float, so inside the GDS:
 *   - uo_out[7:2] must be tied to VGND
 *   - uio_out[7:3] and uio_out[1:0] must be tied to VGND
 *   - uio_oe must be 8'b0000_0100: only uio[2] (MISO) drives out,
 *     so uio_oe[2] ties to VDPWR and every other bit to VGND
 * Miss these and precheck fails late, after the layout is drawn.
 *
 * Pin mapping (from the project register map):
 *   uio[0] SPI CS_N   in        uo_out[0] PWM 0 (drives DAC filter)
 *   uio[1] SPI MOSI   in        uo_out[1] PWM 1
 *   uio[2] SPI MISO   out
 *   uio[3] SPI SCK    in
 *   ua[0] VREF   ua[1] bias monitor
 *   ua[2] UNUSED -- pwm_dac descoped 2026-11-14. Keep all
 *                  met4 and vias 0.5 um clear of it.
 *   ua[7:3] unused -- declared because the template declares them;
 *                     only ua[5:0] are connectable, and only the 3
 *                     you paid for are bonded.
 * ============================================================
 */

`default_nettype none

module tt_um_bvm_mixed_signal_tile (
    input  wire       VGND,
    input  wire       VDPWR,    // 1.8v power supply
//  input  wire       VAPWR,    // 3.3v supply -- needs a different
//                              // template and uses_vapwr: true.
//                              // This tile is 1.8 V only.
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (1 = output)
    inout  wire [7:0] ua,       // Analog pins, only ua[5:0] usable
    input  wire       ena,      // always 1 when powered
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);

    // Intentionally empty: see "WHY THE BODY IS EMPTY" above.

endmodule

`default_nettype wire

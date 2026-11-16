`timescale 1ns / 1ps

module pwm (
    input wire clk,
    input wire rst_n,

    input wire enable,
    input wire width_sel,
    input wire [7:0] duty,

    output reg pwm_out
);

    // ==========================================
    // INTERNAL PHASE COUNTER
    // ==========================================

    reg [7:0] phase;

    wire [5:0] duty_6;

    assign duty_6 = duty[7:2];

    // ==========================================
    // PWM GENERATION
    // ==========================================

    always @(posedge clk or negedge rst_n) begin

        if (!rst_n) begin

            phase   <= 8'd0;
            pwm_out <= 1'b0;

        end

        else if (!enable) begin

            phase   <= 8'd0;
            pwm_out <= 1'b0;

        end

        else begin

            // ==================================
            // 8-BIT PWM MODE
            // ==================================

            if (width_sel) begin

                if (duty == 8'h00)
                    pwm_out <= 1'b0;

                else if (duty == 8'hFF)
                    pwm_out <= 1'b1;

                else
                    pwm_out <= (phase < duty);

                phase <= phase + 8'd1;

            end

            // ==================================
            // 6-BIT PWM MODE
            // ==================================

            else begin

                if (duty_6 == 6'd0)
                    pwm_out <= 1'b0;

                else if (duty_6 == 6'h3F)
                    pwm_out <= 1'b1;

                else
                    pwm_out <= (phase[7:2] < duty_6);

                // FIX:
                // Increment the upper six bits.
                // Keep the lower two bits zero.

                phase <= {
                    (phase[7:2] + 6'd1),
                    2'b00
                };

            end

        end

    end

endmodule

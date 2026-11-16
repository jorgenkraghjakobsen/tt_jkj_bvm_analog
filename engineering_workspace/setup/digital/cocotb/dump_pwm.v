// Waveform dump helper for pwm (make WAVES=1).
// Icarus plus cocotb needs an explicit dump module compiled alongside.
module dump_pwm();
    initial begin
        $dumpfile("pwm.vcd");
        $dumpvars(0, pwm);
    end
endmodule

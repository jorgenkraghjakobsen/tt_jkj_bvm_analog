// Waveform dump helper for bg_seq (make WAVES=1).
// Icarus plus cocotb needs an explicit dump module compiled alongside.
module dump_bg_seq();
    initial begin
        $dumpfile("bg_seq.vcd");
        $dumpvars(0, bg_seq);
    end
endmodule

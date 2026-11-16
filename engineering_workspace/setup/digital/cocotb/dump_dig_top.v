// Waveform dump helper for dig_top (make WAVES=1).
// Icarus plus cocotb needs an explicit dump module compiled alongside.
module dump_dig_top();
    initial begin
        $dumpfile("dig_top.vcd");
        $dumpvars(0, dig_top);
    end
endmodule

// Waveform dump helper for spi_slave (make WAVES=1).
// Icarus plus cocotb needs an explicit dump module compiled alongside.
module dump_spi_slave();
    initial begin
        $dumpfile("spi_slave.vcd");
        $dumpvars(0, spi_slave);
    end
endmodule

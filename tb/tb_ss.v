// tb_ss.v — прогон ss_array. Параметры задаются через iverilog -P tb_ss.N=...
// Печатает строку RESULT found=<0|1> mask=<hex> cycles=<dec>, её разбирает Python.
`timescale 1ns/1ps
module tb_ss;
    parameter N = 16;
    parameter K = 2;
    parameter W = 40;
    parameter TFILE = "T.mem";

    reg clk = 0, rst = 1, start = 0;
    always #5 clk = ~clk;                 // 100 МГц в симуляции (на тайминг не влияет)

    reg signed [W-1:0] Tm [0:0];
    initial $readmemh(TFILE, Tm);

    wire done, found;
    wire [N-1:0] mask;
    wire [47:0] cycles;

    ss_array #(.N(N), .K(K), .W(W)) dut (
        .clk(clk), .rst(rst), .start(start), .T(Tm[0]),
        .done(done), .found(found), .mask(mask), .cycles(cycles)
    );

    initial begin
        repeat (3) @(posedge clk);
        rst <= 0;
        @(posedge clk) start <= 1;
        @(posedge clk) start <= 0;
        wait (done);
        @(posedge clk);
        $display("RESULT found=%0d mask=%h cycles=%0d", found, mask, cycles);
        $finish;
    end
endmodule

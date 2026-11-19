// tb_sat.v — прогон sat_brute. Печатает RESULT sat=<0|1> x=<hex> cycles=<dec>.
`timescale 1ns/1ps
module tb_sat;
    parameter N = 16;
    parameter M = 68;
    parameter LOGP = 2;

    reg clk = 0, rst = 1, start = 0;
    always #5 clk = ~clk;

    wire done, sat;
    wire [N-1:0] solution;
    wire [47:0] cycles;

    sat_brute #(.N(N), .M(M), .LOGP(LOGP)) dut (
        .clk(clk), .rst(rst), .start(start),
        .done(done), .sat(sat), .solution(solution), .cycles(cycles)
    );

    initial begin
        repeat (3) @(posedge clk);
        rst <= 0;
        @(posedge clk) start <= 1;
        @(posedge clk) start <= 0;
        wait (done);
        @(posedge clk);
        $display("RESULT sat=%0d x=%h cycles=%0d", sat, solution, cycles);
        $finish;
    end
endmodule

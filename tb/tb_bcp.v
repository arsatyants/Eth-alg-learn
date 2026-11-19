// tb_bcp.v — подаёт на bcp_unit частичные назначения из vec.mem
// (по два слова: assigned, value) и печатает по строке на вектор:
//   V <i> conflict all_sat unit unit_var unit_val
`timescale 1ns/1ps
module tb_bcp;
    parameter N = 16;
    parameter M = 68;
    parameter NV = 100;

    reg clk = 0;
    always #5 clk = ~clk;

    reg [N-1:0] vec [0:2*NV-1];
    initial $readmemh("vec.mem", vec);

    reg [N-1:0] assigned = 0, value = 0;
    wire conflict, all_sat, unit, unit_val;
    wire [15:0] unit_var;

    bcp_unit #(.N(N), .M(M)) dut (
        .clk(clk), .assigned(assigned), .value(value),
        .conflict(conflict), .all_sat(all_sat), .unit(unit),
        .unit_var(unit_var), .unit_val(unit_val)
    );

    integer i;
    initial begin
        for (i = 0; i < NV; i = i + 1) begin
            assigned <= vec[2*i];
            value    <= vec[2*i+1];
            @(posedge clk);          // защёлкнули входы
            @(posedge clk);          // защёлкнули результат
            #1 $display("V %0d %0d %0d %0d %0d %0d", i, conflict, all_sat, unit, unit_var, unit_val);
        end
        $finish;
    end
endmodule

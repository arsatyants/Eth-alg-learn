// ss_array.v — P = 2^K движков ss_engine, делящих пространство 2^N масок.
//
// Маска = {k, low}: старшие K бит (элементы a[NL..N-1]) закреплены за движком k,
// младшие NL = N-K бит каждый движок перебирает сам в коде Грея.
// base[k] = сумма a[NL+i] для единичных бит i числа k (считает host, файл BFILE).
// Время перебора: 2^NL = 2^N / P тактов. Удвоение P снимает ровно одну переменную.
module ss_array #(
    parameter N     = 20,
    parameter K     = 2,                // P = 2^K движков
    parameter W     = 40,
    parameter DFILE = "dtab.mem",
    parameter BFILE = "base.mem"
) (
    input  wire                 clk,
    input  wire                 rst,
    input  wire                 start,
    input  wire signed [W-1:0]  T,
    output reg                  done,
    output reg                  found,
    output reg  [N-1:0]         mask,
    output reg  [47:0]          cycles
);
    localparam P  = 1 << K;
    localparam NL = N - K;

    reg signed [W-1:0] base [0:P-1];
    initial $readmemh(BFILE, base);

    wire [P-1:0]  e_done, e_found, e_busy;
    wire [NL-1:0] e_mask [0:P-1];

    genvar k;
    generate
        for (k = 0; k < P; k = k + 1) begin : eng
            ss_engine #(.NL(NL), .W(W), .DFILE(DFILE)) u (
                .clk(clk), .rst(rst), .start(start),
                .base(base[k]), .T(T),
                .busy(e_busy[k]), .done(e_done[k]),
                .found(e_found[k]), .fmask(e_mask[k])
            );
        end
    endgenerate

    // приоритетный выбор: движок с наименьшим k среди нашедших
    reg          any;
    reg [N-1:0]  pick;
    integer i;
    always @* begin
        any  = 1'b0;
        pick = {N{1'b0}};
        for (i = P - 1; i >= 0; i = i - 1)
            if (e_found[i]) begin
                any  = 1'b1;
                pick = (i << NL) | e_mask[i];
            end
    end

    reg running;
    always @(posedge clk) begin
        if (rst) begin
            running <= 1'b0; done <= 1'b0; found <= 1'b0; mask <= 0; cycles <= 0;
        end else if (start) begin
            running <= 1'b1; done <= 1'b0; found <= 1'b0; cycles <= 0;
        end else if (running) begin
            cycles <= cycles + 1'b1;
            if (any) begin
                running <= 1'b0; done <= 1'b1; found <= 1'b1; mask <= pick;
            end else if (&e_done) begin
                running <= 1'b0; done <= 1'b1;
            end
        end
    end
endmodule

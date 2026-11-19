// sat_brute.v — параллельный перебор 3-SAT: P = 2^LOGP ядер, каждое за такт целиком
// проверяет одно назначение (все M клауз параллельно).
//
// Клауза = две маски: pos (литералы x_i) и neg (литералы ¬x_i).
// Назначение a выполняет клаузу <=> |((a & pos) | (~a & neg)).
// Ядро k проверяет назначение a = {cnt, k}; полный перебор — 2^(N-LOGP) тактов.
// Назначения идут по возрастанию, поэтому найденное решение — минимальное.
// (Расширенная версия для платы с UART: fpga-course/sat-bruteforce.)
module sat_brute #(
    parameter N     = 16,
    parameter M     = 68,
    parameter LOGP  = 2,
    parameter PFILE = "pos.mem",
    parameter NFILE = "neg.mem"
) (
    input  wire          clk,
    input  wire          rst,
    input  wire          start,
    output reg           done,
    output reg           sat,
    output reg  [N-1:0]  solution,
    output reg  [47:0]   cycles
);
    localparam P  = 1 << LOGP;
    localparam CW = N - LOGP;

    reg [N-1:0] pos [0:M-1];
    reg [N-1:0] neg [0:M-1];
    initial begin
        $readmemh(PFILE, pos);
        $readmemh(NFILE, neg);
    end

    reg  [CW-1:0] cnt;
    reg           busy;
    wire [P-1:0]  ok;

    genvar k;
    generate
        for (k = 0; k < P; k = k + 1) begin : core
            wire [N-1:0] a;
            if (LOGP == 0) begin : g0
                assign a = cnt;
            end else begin : g1
                assign a = {cnt, k[LOGP-1:0]};
            end
            reg r;
            integer c;
            always @* begin
                r = 1'b1;
                for (c = 0; c < M; c = c + 1)
                    r = r & (|((a & pos[c]) | (~a & neg[c])));
            end
            assign ok[k] = r;
        end
    endgenerate

    // младшее ядро с ok=1 -> минимальное назначение в этом такте
    reg          hit;
    reg [N-1:0]  first;
    integer i;
    always @* begin
        hit = 1'b0;
        first = {N{1'b0}};
        for (i = P - 1; i >= 0; i = i - 1)
            if (ok[i]) begin
                hit = 1'b1;
                first = (cnt << LOGP) | i;
            end
    end

    always @(posedge clk) begin
        if (rst) begin
            busy <= 1'b0; done <= 1'b0; sat <= 1'b0; cnt <= 0; cycles <= 0; solution <= 0;
        end else if (start) begin
            busy <= 1'b1; done <= 1'b0; sat <= 1'b0; cnt <= 0; cycles <= 0;
        end else if (busy) begin
            cycles <= cycles + 1'b1;
            if (hit) begin
                busy <= 1'b0; done <= 1'b1; sat <= 1'b1; solution <= first;
            end else if (&cnt) begin
                busy <= 1'b0; done <= 1'b1;
            end else
                cnt <= cnt + 1'b1;
        end
    end
endmodule

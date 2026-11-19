// bcp_unit.v — Boolean Constraint Propagation за один такт.
//
// Правильное место FPGA рядом с умным алгоритмом: DPLL/CDCL работает на ARM и
// уменьшает основание экспоненты, а самый частый шаг — проход по всем клаузам
// в поиске конфликта и unit-клауз (80–90% времени CDCL) — делается в PL сразу
// для всех M клауз.
//
// Частичное назначение: assigned[v]=1 — переменная задана, value[v] — её значение.
// Для каждого литерала:  T = задан и истинен,  F = задан и ложен,  U = свободен.
//   клауза выполнена  <=> есть T
//   конфликт          <=> все три F
//   unit              <=> нет T и ровно один U (его и надо сделать истинным)
// Выход: conflict (есть конфликт), all_sat (все клаузы выполнены),
//        unit + unit_var/unit_val для первой (наименьший индекс) unit-клаузы.
//
// Клаузы — константы из файла: на клаузу три слова {sign, var[VW-1:0]},
// sign=1 — отрицание. После синтеза каждый литерал — это просто провод от
// assigned/value, а клауза — несколько LUT.
module bcp_unit #(
    parameter N     = 16,
    parameter M     = 68,
    parameter LFILE = "lits.mem"
) (
    input  wire          clk,
    input  wire [N-1:0]  assigned,
    input  wire [N-1:0]  value,
    output reg           conflict,
    output reg           all_sat,
    output reg           unit,
    output reg  [15:0]   unit_var,     // номер переменной с 0
    output reg           unit_val
);
    localparam VW = (N <= 1) ? 1 : $clog2(N);

    reg [VW:0] lits [0:3*M-1];
    initial $readmemh(LFILE, lits);

    reg [M-1:0] c_sat, c_conf, c_unit;
    reg [15:0]  c_uvar [0:M-1];
    reg         c_uval [0:M-1];

    integer c, t;
    reg [VW-1:0] v;
    reg          s, isT, isF;
    reg [1:0]    nU;
    always @* begin
        for (c = 0; c < M; c = c + 1) begin
            c_sat[c]  = 1'b0;
            nU        = 2'd0;
            c_uvar[c] = 16'd0;
            c_uval[c] = 1'b0;
            for (t = 0; t < 3; t = t + 1) begin
                v   = lits[3*c+t][VW-1:0];
                s   = lits[3*c+t][VW];
                isT = assigned[v] & (value[v] ^ s);
                isF = assigned[v] & ~(value[v] ^ s);
                if (isT) c_sat[c] = 1'b1;
                if (!assigned[v]) begin
                    nU = nU + 1'b1;
                    c_uvar[c] = v;
                    c_uval[c] = ~s;            // сделать литерал истинным
                end
            end
            c_conf[c] = ~c_sat[c] & (nU == 2'd0);
            c_unit[c] = ~c_sat[c] & (nU == 2'd1);
        end
    end

    integer i;
    reg        u_any;
    reg [15:0] u_var;
    reg        u_val;
    always @* begin
        u_any = 1'b0; u_var = 16'd0; u_val = 1'b0;
        for (i = M - 1; i >= 0; i = i - 1)
            if (c_unit[i]) begin
                u_any = 1'b1; u_var = c_uvar[i]; u_val = c_uval[i];
            end
    end

    always @(posedge clk) begin
        conflict <= |c_conf;
        all_sat  <= &c_sat;
        unit     <= u_any & ~(|c_conf);
        unit_var <= u_var;
        unit_val <= u_val;
    end
endmodule

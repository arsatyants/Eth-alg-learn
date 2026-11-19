// ss_engine.v — один движок Subset Sum: перебор 2^NL подмножеств в коде Грея,
// одно подмножество за такт.
//
// Маска в такте cnt:   g(cnt) = cnt ^ (cnt >> 1)
// Переход cnt -> cnt+1 меняет ровно один бит маски: idx = ctz(cnt+1).
// Новое значение этого бита dir = g(cnt+1)[idx]:
//     dir = 1 -> элемент вошёл в подмножество:  sum += a[idx]
//     dir = 0 -> элемент вышел:                 sum -= a[idx]
//
// Вместо мультиплексора a[idx] (NL:1 шириной W ≈ 10 LUT/бит) приращение берётся из
// таблицы dtab[{idx,dir}] = dir ? +a[idx] : -a[idx]. Таблица на 2*NL <= 64 слова
// ложится в распределённую RAM: RAM64X1 = 1 LUT на бит, то есть ~W LUT на движок.
//
// base — сумма «старших» элементов, закреплённых за этим движком (см. ss_array.v).
module ss_engine #(
    parameter NL    = 10,              // сколько элементов перебирает движок
    parameter W     = 40,              // разрядность сумм
    parameter DFILE = "dtab.mem"       // 2*NL слов: [2*i] = -a[i], [2*i+1] = +a[i]
) (
    input  wire                 clk,
    input  wire                 rst,
    input  wire                 start,
    input  wire signed [W-1:0]  base,
    input  wire signed [W-1:0]  T,
    output reg                  busy,
    output reg                  done,
    output reg                  found,
    output reg  [NL-1:0]        fmask
);
    localparam IW = (NL <= 1) ? 1 : $clog2(NL);

    (* ram_style = "distributed" *)
    reg signed [W-1:0] dtab [0:2*NL-1];
    initial $readmemh(DFILE, dtab);

    reg  [NL-1:0] cnt;
    wire [NL-1:0] nxt  = cnt + 1'b1;
    wire [NL-1:0] gcur = cnt ^ (cnt >> 1);
    wire [NL-1:0] gnxt = nxt ^ (nxt >> 1);

    // idx = ctz(nxt): приоритетный шифратор младшей единицы
    reg [IW-1:0] idx;
    integer j;
    always @* begin
        idx = {IW{1'b0}};
        for (j = NL - 1; j >= 0; j = j - 1)
            if (nxt[j]) idx = j[IW-1:0];
    end

    wire               dir   = gnxt[idx];
    wire signed [W-1:0] delta = dtab[{idx, dir}];

    reg signed [W-1:0] sum;            // сумма подмножества gcur (вместе с base)
    wire last = &cnt;                  // cnt = 2^NL - 1: последняя маска

    always @(posedge clk) begin
        if (rst) begin
            busy <= 1'b0; done <= 1'b0; found <= 1'b0;
            cnt <= {NL{1'b0}}; sum <= {W{1'b0}}; fmask <= {NL{1'b0}};
        end else if (start) begin
            busy <= 1'b1; done <= 1'b0; found <= 1'b0;
            cnt <= {NL{1'b0}}; sum <= base;
        end else if (busy) begin
            // сравнение и сумматор работают параллельно от одного регистра sum
            if (sum == T) begin
                found <= 1'b1; fmask <= gcur; busy <= 1'b0; done <= 1'b1;
            end else if (last) begin
                busy <= 1'b0; done <= 1'b1;
            end else begin
                cnt <= nxt;
                sum <= sum + delta;
            end
        end
    end
endmodule

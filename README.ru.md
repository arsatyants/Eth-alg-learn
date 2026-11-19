# Eth-alg-learn

*English: [README.md](README.md)*

Учебный проект о **гипотезе экспоненциального времени (ETH)** и экспоненциальных алгоритмах.
Он показывает, почему алгоритм уменьшает **основание** экспоненты, а FPGA меняет только **константу**.
Каждое утверждение проверяется тремя способами: математический вывод → эксперимент на Python →
Verilog-модуль, запущенный в Icarus Verilog.

Главный файл — [`notebooks/eth_alg_learn.ipynb`](notebooks/eth_alg_learn.ipynb). Он уже выполнен,
графики и выводы видны прямо на GitHub.

## Содержание ноутбука

| № | Раздел | Ключевой результат |
|---|---|---|
| 1 | Экспонента как стена | ускорение ×S даёт только +log_c S к n; алгоритм умножает n на ln c / ln c' |
| 2 | 3-SAT, ETH, SETH, лемма о разрежении | фазовый переход у m/n ≈ 4.27 (эксперимент) |
| 3 | Ветвление и рекурренты | 1 = Σ c^(−dᵢ): 1.839ⁿ, 1.618ⁿ, 1.466ⁿ; сверка с корнями многочлена |
| 4 | Перебор → бэктрекинг → ветвление по клаузе → DPLL | измеренные основания: 2.05 → 1.39 → 1.11 → 1.08 |
| 5 | Алгоритм Шёнинга | вывод (4/3)ⁿ через случайное блуждание; эксперимент |
| 6 | Subset Sum | наивно O(n·2ⁿ), код Грея O(2ⁿ), meet-in-the-middle O(2^(n/2)) |
| 7 | FPGA: `sat_brute.v` | Icarus: такты = 2^(n−LOGP), решение совпадает с Python |
| 8 | FPGA: `ss_engine.v` | мультиплексор против LUTRAM: ~540 → ~140 LUT на движок |
| 9 | FPGA правильно: `bcp_unit.v` | трасса DPLL → BCP за такт, 0 расхождений |
| 10 | Сводная картина и граница ETH | «сначала основание, потом константа» |
| 11 | Упражнения | |

## Структура

```
ethlearn/           Python-библиотека
  sat.py            генераторы 3-SAT; перебор, бэктрекинг, ветвление по клаузе, DPLL (с трассой), Шёнинг
  recurrence.py     branching number: бисекция и корни характеристического многочлена
  subset_sum.py     наивный перебор, код Грея, meet-in-the-middle, ДП
  fpga.py           модель времени и ресурсов XC7Z010, генерация .mem, запуск Icarus
rtl/
  sat_brute.v       P = 2^LOGP ядер, одно назначение 3-SAT за такт на ядро
  ss_engine.v       движок Subset Sum: подмножество за такт, код Грея, таблица ±a в LUTRAM
  ss_array.v        2^K движков делят пространство масок
  bcp_unit.v        Boolean Constraint Propagation всех клауз за один такт
tb/                 тестбенчи Icarus (tb_ss.v, tb_sat.v, tb_bcp.v)
tools/
  build_notebook.py собирает и выполняет ноутбук
  check_rtl.py      регрессия RTL против Python-эталонов
figures/            графики из ноутбука
```

## Запуск

```bash
pip install -r requirements.txt
sudo apt install iverilog          # для разделов 7–9
python3 tools/check_rtl.py         # ALL PASS
jupyter lab notebooks/eth_alg_learn.ipynb
# или пересобрать и выполнить целиком (~2.5 мин):
python3 tools/build_notebook.py --execute
```

## Железо

Целевая плата — 7Z-Lite (XC7Z010, 17 600 LUT6, кварц 50 МГц). RTL проверен только в симуляции (Icarus Verilog).
Оценки LUT в ноутбуке модельные, точные цифры даст синтез в Vivado.
Расширенная версия перебора 3-SAT для платы, с UART и скриптами Vivado, лежит в
[`fpga-course/sat-bruteforce`](https://github.com/arsatyants/fpga-course/tree/master/sat-bruteforce).

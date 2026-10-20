# 更新记录
## 0.31.7 — 2026-10-20（真图回归缺陷修复：候选门槛 + DWG 空解码自动复扫）

- `run_real_dwg_regression.py`：无显式 expect 时，缺省候选门槛由“最后一个细分域
  ≥1”改为“整套识图包至少产出一个领域候选”，避免把本无该细分域的真实图纸误判为缺陷
  （电气/园林/结构 9 条真实 DWG 由“候选不足”恢复通过）。
- `cad_scan.py`：DWG 直读文字/图层为空时自动尝试 LibreDWG→DXF 复扫（无需显式
  `--dwg-dxf-fallback`），并把 `解码失败 / section map has no entries` 纳入触发词；
  reg-0169（R2007 section map 无条目）经复扫产出结构几何候选。
- 回归：真实 DWG 子集 20 条由 10 通过/10 失败 → 20/20 通过；全量自测 205/205 保持全绿，
  schema/cad_validate 契约校验继续通过，`final_quantity=false` 未改动。
- `manifest.json` 同步升版 0.31.7。

## 0.31.6 — 2026-10-20（CI / self_test 统一自测回归闭环）
 — 2026-10-20（CI / self_test 统一自测回归闭环）

- 新增 `scripts/self_test.py` + `scripts/self_test.sh` 统一入口：一条命令跑
  doctor → 全量 unittest → schema/cad_validate 契约校验 → 样例 DXF 回归 →
  坏文件快速失败不变量 → 可选真实 DWG 回归，输出“三合一” JSON + Markdown 报告。
- `schemas/*.schema.json` 纳入自测：内置零依赖轻量 JSON Schema 校验器（无需
  jsonschema 包），对 `examples/qto-sample` 样例做正/负向不变量校验，并继续用
  `scripts/cad_validate.sh` 校验全部 v0 契约样例。
- 新增长效自动化用例 `scripts/tests/test_self_test.py`（schema 正/负向、
  快速跳过 CLI、缺 manifest 时回归记 skipped）；全量自测 201 → 205 项全部通过，
  三合一闭环无 manifest 运行 6 步：5 通过 + 1 跳过。
- 用法已写进 `README.md` 与 `SKILL.md`；`manifest.json` 同步升版 0.31.6。

## 0.31.5 — 2026-10-20（可靠性加固：快速失败/批量跳档/PDF 复核截图）

- 新增 `scripts/cad_preflight.py` 轻量预检（只读前 4KB，<5 秒）：空文件、<1KB、魔数错误
  （非 AC#### / DXF-SECTION / %PDF-）直接快速失败；不支持 DWG 版本报“不支持版本”。
- `cad_scan / read_cad / convert_dwg` 入口接入预检；批量 `cad_batch` 用同一预检，
  加密 DWG/不支持版本/超时/内存看门狗终止在台账“缺口/失败原因”里明确区分，
  不中断整批。
- `cad_batch.run_cad_scan` 增加硬超时（超时 rc=124）并把退出码 -9/内存闸关键词翻译为
  “内存看门狗终止”；新增 `rc_reason()` 原因翻译。
- `cad_pdf_ocr` 自动输出可疑页复核截图到 `outdir/_review/<图名>-p<页码>.png` 与
  `_review/index.json`：OCR 失败页、扫描页 OCR 无文字、整页平均置信 <60%、低置信区块
  （<40%）触发；候选带 `review_image` 字段；`--no-review` 可关闭。
- 保持 `cad-file-reader/v0` 契约不变，`cad_validate.sh` 校验继续通过。
- 新增 6 项自测（快速失败/原因翻译/批量不中断）+ PDF 复核字段不破坏 v0 校验；
  全量测试 189 → 201 全部通过。
- 回归：`examples/sample_room.dxf`（DXF 正常）+ 空文件 + 坏魔数 + 不支持 AC9999 版本头
  全部按预期：样例正常出结果，坏文件 <1s 快速失败并留原因。


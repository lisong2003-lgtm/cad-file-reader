# cad-file-reader 自测/回归三合一报告

- 生成时间：`2026-11-08T12:48:02+08:00`
- 技能根目录：`/Users/lis/Documents/Codex/2026-11-08/agent-users-lis-codex-memory-recovery/work/pub/build/cad-file-reader/github`
- 总体状态：**PASS**（通过 5 / 6，跳过 1，失败 0）

## 1) doctor 环境体检

- `dxf`：不可用
- `dwg`：不可用
- `pdf_vector`：可用
- `pdf_raster_ocr`：可用
- `measure`：不可用
- `qto_linkage`：可用
- `lis_skill_bus`：已安装

## 2) 全量自测

- 运行：265 项
- 失败：0，错误：0

## 3) schema + cad_validate 契约校验

- `candidate-v0.schema.json`：OK（样例 5 个，含负向不变量）
- `qto-project-v1.schema.json`：OK（样例 5 个，含负向不变量）
- cad_validate.py 样例：OK（5 个）

## 4) 样例回归（sample_room.dxf）

- cad_scan rc=0，文字 2 条，文件 1 个，契约校验通过

## 5) 坏文件不变量

- OK（0.0s）
  - 空文件：OK — 空文件（0 字节）
  - 坏魔数：OK — 魔数/头部不是标准 DWG、DXF 或 PDF（可能是其它文件或已损坏）
  - 快速失败<5s：OK — 0.0s

## 6) 真实 DWG 回归

- 状态：skipped

---
*三合一报告由 `scripts/self_test.py` 生成。*
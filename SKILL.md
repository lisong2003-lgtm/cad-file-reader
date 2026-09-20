---
name: cad-file-reader
slug: cad-file-reader
displayName: CAD 图纸识图与证据提取
version: 0.18.0
author: lis
license: CC-BY-NC-SA-4.0
description: 本地读取 AutoCAD DWG/DXF/DWT，提取图层、文字、块、图框、几何、建筑/结构/安装/钢结构/市政识图候选、系统拓扑、长度/面积/体积测量候选及规范图集元数据，并保留证据坐标和复核原因。仅输出识图与测量候选（final_quantity=false），不计算最终工程量、扣减、材料量、造价或结算量；算量交给专项技能。
---

# CAD 图纸识图与证据提取（cad-file-reader）

本技能只做**识图、证据提取、候选解释和测量候选**，可输出长度、面积、体积的识图候选值、计算式和复核边界；不把候选值冒充最终工程量、清单量、材料量、造价或结算量。结构混凝土/钢筋算量已迁到 `tujian-suanliang`（本机目录 `shangwu-suanliang`），装饰、安装、钢结构、市政算量分别交给对应专项 skill。

## 执行原则

- 先用低内存 `cad_scan` 读文字、图层、块名、图框和几何候选；确需实体树/渲染时再用 `read_cad`。
- 自动结果必须带证据坐标、图框、图层、口径和复核边界；缺输入时列缺口，不编造数量或合规结论。
- 规范/图集资料只做元数据与版本风险提示，不复制全文、不输出条文符合性结论。
- 命令均相对技能根目录执行；输出文件写入当前项目工作目录，不写系统目录。
- 大图先扫描、按需局部展开；高内存/高 CPU 立即暂停。

## 快速读取

```bash
# 大图优先：构件编号、图层、关键词、图框
scripts/cad_scan.sh 图纸.dwg --only 梁,板,柱,墙 --cluster 1500 --format md -o 图纸扫描

# 关键词与原文证据
scripts/cad_scan.sh 图纸.dwg --search "板厚|C30|抗震等级|保护层|22G101"

# 需要识图几何和详情时
scripts/cad_scan.sh 图纸.dwg --only 梁,板,柱,墙 --with-mtext --with-geom \
  --cluster 1500 --detail-json 图纸详情.json --format all -o 图纸扫描
```

口径：`原文次数`不是根数；`--count-by auto`优先平法集中标注，缺集中标注退回标注位置去重。
`--with-geom`提供图面几何候选和证据；需要长度/面积/体积候选时再用 `cad_measure`，输出始终带 `final_quantity=false`。

## 测量候选（长度 / 面积 / 体积）

从 `cad_scan` 详情或装饰/安装/钢结构/市政识图 JSON 生成可追溯测量候选：

```bash
scripts/cad_measure.sh 描述几何/图纸详情.descriptive.json --out-dir 测量候选

# 显式覆盖比例/单位；缺比例或单位时保留图面值并转 review
scripts/cad_measure.sh 安装识图/安装详情.mep.json   --scale 1:100 --unit mm --coordinate-space model --out-dir 测量候选

# 已有面积候选且设计明确厚度时，生成待复核体积候选
scripts/cad_measure.sh 描述几何/图纸详情.descriptive.json --thickness-m 0.10 --out-dir 测量候选
```

输出 `cad-measurement-candidates.json/md/csv`，每条包含 `kind/value/unit/value_drawing_units/scale/space/basis/method/formula/status/confidence/review_reason/evidence/source_schema/source_id/final_quantity=false`。闭合多边形用鞋带公式，显式文字测量值可直接采用，外接框面积只作证据；MEP/钢结构/市政单段长度只作识图证据。方法、比例单位规则和专项交接见 `packs/measurement-candidates/SKILL.md`。

本层不输出最终工程量；扣减、重叠、做法、损耗、分账、清单量和材料量由专项算量 skill 负责。

## 装饰识图与中间数据

建筑图/装修表转房间、墙面、地面、顶棚分区、楼梯/坡道/台阶初稿、外墙分格/保温分区、门窗洞口和做法候选：

```bash
scripts/cad_descriptive_geometry.sh 图纸详情.json --out-dir 描述几何
```

方法、投影校验与输出契约见 `packs/descriptive-geometry/SKILL.md`。只输出装饰算量前的中间数据，不直接出量。

## 安装识图与中间数据

电气、给排水、消防水、暖通、火灾报警、应急照明、弱电和燃气图纸先转成安装识图候选：

```bash
scripts/cad_scan.sh 安装图.dwg --with-mtext --with-insert \
  --with-geom --with-geom-layer \
  --detail-json 安装详情.json --format json -o 安装扫描

scripts/cad_mep_geometry.sh 安装详情.json --out-dir 安装识图
```

输出图纸类型、专业系统、路由段、设备、标注、立管、竖向路由、系统拓扑候选、坐标证据和 `review`。安装算量、材料量和损耗交给 `anzhuang-suanliang`。

## 钢结构识图与中间数据

钢结构设计说明、布置图、构件图、节点详图、材料表和预拼装图先转成构件、截面、连接、材料、涂装、节点、轴网/标高和几何候选：

```bash
scripts/cad_scan.sh 钢结构图.dwg --with-mtext --with-insert \
  --with-geom --with-geom-layer \
  --detail-json 钢结构详情.json --format json -o 钢结构扫描

scripts/cad_steel_geometry.sh 钢结构详情.json --out-dir 钢结构识图
```

本层只做识图，不输出重量、面积、长度汇总或材料量。钢材重量、涂装面积、螺栓数量和焊缝长度交给钢结构专项算量 skill。

## 市政专业识图与中间数据

道路、排水、管网、桥梁、涵洞、隧道、挡墙、交通和道路照明等市政图纸先转成图纸类型、专业系统、道路/桥隧/管网构件、材料、桩号、标高、坐标和几何候选：

```bash
scripts/cad_scan.sh 市政图.dwg --with-mtext --with-insert \
  --with-geom --with-geom-layer \
  --detail-json 市政详情.json --format json -o 市政扫描

scripts/cad_municipal_geometry.sh 市政详情.json --out-dir 市政识图
```

本层只做识图，不输出面积、长度汇总、数量或材料量。市政算量交给市政专项 skill。

## DWG 转 DXF

```bash
scripts/convert_dwg.sh 图纸.dwg --out 图纸.dxf
scripts/convert_dwg.sh 图纸目录 --recursive --out 输出目录
```

默认输出已存在不覆盖；大文件有 200MB 入口闸和内存看门狗，必要时才显式放开。

## 说明、规范与图集辅助

```bash
# 1. 抽取说明文字、标注和图纸参数
scripts/cad_scan.sh 图纸.dwg --with-mtext --with-geom \
  --detail-json 图纸详情.json --format json -o 图纸扫描

# 2. 解读构件规则、引用目录和缺失输入
scripts/cad_interpret.sh --scan 图纸扫描.json --detail 图纸详情.json \
  --rules rules --format all -o 图纸解读

# 3. 定位规范/图集元数据、版本风险、参数冲突和资料入口
scripts/cad_normative.sh --scan 图纸扫描.json --detail 图纸详情.json \
  --rules rules --format all -o 规范辅助
```

规范辅助输出：已索引/未索引编号、现行/旧版/待确认状态、知识库相对路径或在线入口、缺少的设计输入、多参数冲突。`rules/standards.json`只保存编号、名称、专业、状态和资料入口元数据；条文适用性以图纸指定版本和授权全文为准。

## 结构算量的归属

原 `cad-file-reader` 内的梁、板、柱、墙、楼梯、洞口、预制底板、混凝土分账和结构算量流水线已迁移到：

- `tujian-suanliang`（本机目录 `shangwu-suanliang`）
- 统一入口：在土建算量技能目录执行 `scripts/run_qty.sh advanced ...` 或 `scripts/run_qty.sh pipeline ...`
- 迁移脚本仍通过 `CAD_SKILL_DIR` 调用本技能的 `cad_scan`/`cad_interpret` 识图底座。

本技能不再提供 `cad_quantity_pipeline.sh`、梁板柱墙混凝土方量、轴线面积、构件体积或材料量输出。

## 工作流

1. 识别 DWG/DXF/DWT 和大小；大图禁止直接全量实体树解析。
2. `cad_scan` 建立文字/图层/块名/图框/几何候选索引，保留原文证据。
3. 说明与规范任务运行 `cad_interpret` + `cad_normative`；装饰/安装/钢结构/市政识图读取对应 pack。
4. 需要算量时把识图结果交给 `tujian-suanliang`、`zhuangshi-suanliang`、`anzhuang-suanliang` 或对应专项 skill。
5. 同一张图重复查询优先复用已有 scan/detail/索引，不重复解析大图。

## 边界

- 不做设计合规审查、施工方案判断、清单计价、结算审计或规范条文解释。
- 测量候选不是最终工程量；专项算量 skill 必须继续完成扣减、重叠、做法映射、损耗、分账和台账。
- 不输出最终工程量、材料量、造价或结算量；只输出识图候选、几何证据、测量候选（`final_quantity=false`）和复核原因。
- 自动提取不能替代设计单位、翻样、清单编制和正式授权规范全文。
- 不把公司内部路径、项目结果或规范全文写入技能发布内容。

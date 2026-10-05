---
name: cad-file-reader
slug: cad-file-reader
displayName: CAD 图纸识图与证据提取
version: 0.25.0
author: lis
license: CC-BY-NC-SA-4.0
description: 本地读取 AutoCAD DWG/DXF/DWT，提取图层、文字、块、图框、几何、建筑/结构/总图场地/安装/电气（含消防/弱点/智能化）/钢结构/市政/给排水暖通/精装修室内/幕墙/人防/预制装配识图候选、系统拓扑、长度/面积/体积测量候选及规范图集元数据，并保留证据坐标和复核原因。仅输出识图与测量候选（final_quantity=false），不计算最终工程量、扣减、材料量、造价或结算量；算量交给专项技能。内置 P0–P5 优化：统一候选契约/置信度分层、大图缓存与局部解析、图层/块语义、MEP 拓扑增强、图纸对比。
---

# CAD 图纸识图与证据提取（cad-file-reader）

本技能只做**识图、证据提取、候选解释和测量候选**，可输出长度、面积、体积的识图候选值、计算式和复核边界；不把候选值冒充最终工程量、清单量、材料量、造价或结算量。结构混凝土/钢筋算量已迁到 `tujian-suanliang`（本机目录 `shangwu-suanliang`），装饰、安装、钢结构、市政算量分别交给对应专项 skill。

## 执行原则

- 先用低内存 `cad_scan` 读文字、图层、块名、图框和几何候选；确需实体树/渲染时再用 `read_cad`。
- 自动结果必须带证据坐标、图框、图层、口径和复核边界；缺输入时列缺口，不编造数量或合规结论。
- 规范/图集资料只做元数据与版本风险提示，不复制全文、不输出条文符合性结论。
- 命令均相对技能根目录执行；输出文件写入当前项目工作目录，不写系统目录。
- 大图先扫描、按需局部展开；高内存/高 CPU 立即暂停。
- 首次扫描可用 `--cache-dir` 建立本机证据缓存；同图重复查询命中缓存。缓存只保存识图证据，不保存最终工程量。

## 统一候选契约（cad-file-reader/v0）

装饰、安装、钢结构、市政和测量候选 JSON 会额外写入 `contract`：

- `candidates[]` 只放 `confirmed_evidence` 和 `inferred_candidate`；`review_candidates[]` 只放 `review_required`。
- `confirmed_evidence`：有直接文字、图层、几何、块或标注证据，且置信度 ≥ 0.90。
- `inferred_candidate`：由邻近关系、图层语义、块内容或规则推断，置信度 0.50–0.89。
- `review_required`：低置信、缺比例/单位/图层/块定义、文字绑定不明、几何冲突、重复、图框外或几何不完整；不进入默认汇总主线。
- `review_reasons[]` 使用标准英文词表，`review_notes` 保留中文说明；`source_schema` 固定为 `cad-file-reader/v0`，`final_quantity` 固定为 `false`。
- 交付或交接前可校验：`scripts/cad_validate.sh 输出.json`。

## 图层/块语义与图纸对比

在 `cad_scan` 详情 JSON 上生成图层语义、块语义、块实例关联、MEP 端点/设备/立管关联候选和图纸变化候选；低置信或冲突项只进入 `review_candidates[]`，不进入默认汇总主线，也不改写工程量。

```bash
# P2/P3：图层与块语义候选；匿名/无语义块会标 missing_block_definition 或低置信推断
scripts/cad_semantics.sh 图纸详情.json --out-dir 语义识图 \
  --max-layers 2000 --max-blocks 2000 --max-instances 2000 --link-radius 3000

# 图例知识表候选（轻量词库：块名/图层/文字关键词匹配，不引视觉模型）
scripts/cad_legend.sh 图纸详情.json --out-dir 图例识图 --max-matches 2000

# P4：安装专业管段端点、设备、立管和系统冲突关联候选
scripts/cad_mep_geometry.sh 安装详情.json --out-dir 安装识图

# P5：同图重复对比应返回 0 变化；不同图输出图层/块/文字/几何增删与移动候选
scripts/cad_compare.sh 基准详情.json 目标详情.json \
  --out-dir 图纸对比 --tolerance 1.0 --max-changes 5000
```

图例候选沿用统一契约：`legend_matches` 输出专业、语义、命中关键词、块/图层/文字证据和 `discipline_refs`；`rules/legends.json` 内置 14 组关键词与 12 组符号指纹，块引用优先走符号指纹匹配，同名文本不重复抢占。语义与变化候选沿用统一契约：`semantic_layers`、`semantic_blocks`、`block_instances`、`mep_relations`、`drawing_changes`。候选可带可选 `rotation`（文字旋转角）、`confidence_scores`（证据子项强度）和 `discipline_refs`（跨专业视角），全部固定 `final_quantity=false`；专用技能必须自行核对后再做算量。旋转角参与位置分桶（0-180°按 5° 归一）：同一图框内同位置但旋转不同会拆为独立标注位置，旋转相同则按原规则合并。

## 快速读取

```bash
# 大图优先：构件编号、图层、关键词、图框
scripts/cad_scan.sh 图纸.dwg --only 梁,板,柱,墙 --cluster 1500 --format md -o 图纸扫描

# 关键词与原文证据
scripts/cad_scan.sh 图纸.dwg --search "板厚|C30|抗震等级|保护层|22G101"

# 需要识图几何和详情时
scripts/cad_scan.sh 图纸.dwg --only 梁,板,柱,墙 --with-mtext --with-geom \
  --cluster 1500 --detail-json 图纸详情.json --format all -o 图纸扫描

# 大图首次全量扫描并建本机证据缓存
scripts/cad_scan.sh 图纸.dwg --with-geom --with-geom-layer \
  --cache-dir /tmp/cad-file-reader-cache --format all -o 图纸扫描

# 同图重复查询：命中缓存后按图面矩形局部读取
scripts/cad_scan.sh 图纸.dwg --with-geom --with-geom-layer \
  --cache-dir /tmp/cad-file-reader-cache --roi 0,0,30000,20000 --format json -o 局部读取

# 同图重复查询：命中缓存后按图框编号局部读取
scripts/cad_scan.sh 图纸.dwg --with-geom --with-geom-layer \
  --cache-dir /tmp/cad-file-reader-cache --sheet 1 --format json -o 图框读取
```

缓存键使用源文件 SHA-256 和影响证据内容的扫描参数档；`--roi`、`--sheet` 只做查询过滤。ROI 几何使用预归一化 bbox 索引，缓存写入先批量落库、延后建索引。JSON 的 `cache.hits/misses` 记录命中情况。局部结果只返回命中范围内的证据，不混入整图块统计。
缓存只保存识图证据，不保存最终工程量、扣减、材料量、造价或结算量。
JSON 汇总输出 `cache.read_ms/write_ms/db_files/db_bytes`；每个文件输出 `cache_read_ms/cache_write_ms/cache_bytes`。
缓存盘点/清理用 `scripts/cad_cache_admin.sh 缓存目录`：默认只读盘点；`--cleanup` 生成计划，`--apply` 才删除。temp/legacy 默认进入计划；corrupt/unknown 永不删除；current 默认保留，必须显式 `--include-current` 且提供 `--max-age-days` 或 `--max-total-mb`。

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

## 电气识图与中间数据

变配电、照明、动力、应急照明、火灾报警、安防、弱电智能化和防雷接地图纸先转成电气识图候选：

```bash
scripts/cad_scan.sh 电气图.dwg --with-mtext --with-insert \
  --with-geom --with-geom-layer \
  --detail-json 电气详情.json --format json -o 电气扫描

scripts/cad_electrical_geometry.sh 电气详情.json --out-dir 电气识图
```

输出图纸类型、专业系统、桥架/母线/导管/电缆/导线路由段、配电箱/柜、灯具、开关插座、探测器、防雷接地设备、消防（消防水/喷淋/气体灭火/防排烟/防火卷帘/消防联动/消防泵）、弱点/弱电（综合布线/CCTV/门禁/广播）、智能化（BAS/能耗计量/智能照明/IBMS）、回路编号、回路规格标注、领域分组字段、坐标证据和 `review`。本层只做识图，不展开芯数/线长、不做负荷/照度/母排计算；电气算量材料量交给 `anzhuang-suanliang` 或下游专项 skill。方法与规则见 `packs/electrical-geometry/SKILL.md`。

本机真实电气/结构/总图场地 DWG 回归用 `scripts/run_real_dwg_regression.sh --manifest 真图清单.json`，清单里每条 case 可写 `kind=electrical|structural|site|hvac_plumbing|interior_finish|curtain_wall|civil_defense|precast`；清单放在技能包之外并在发布前脱敏。

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

## 结构识图与中间数据

结构施工图先转成图纸类型、结构系统、构件（梁/板/柱/墙/基础/楼梯/洞口）、配筋、编号、节点和轴网候选；钢筋等级/直径@间距、锚固、搭接和洞口加强只作识图证据：

```bash
scripts/cad_scan.sh 结构图.dwg --with-mtext --with-insert \
  --with-geom --with-geom-layer \
  --detail-json 结构详情.json --format json -o 结构扫描

scripts/cad_structural_geometry.sh 结构详情.json --out-dir 结构识图
```

本层只做识图，不输出混凝土方量、钢筋吨位、锚固长度、体积或材料量；配筋标注不自动换算成下料/翻样量，交给 `tujian-suanliang` 或结构专项 skill。

## 总图/场地识图与中间数据

总平面、竖向设计、管线综合、道路、挡土墙/边坡、停车和景观图纸先转成图纸类型、系统、场地构件（红线/道路/停车/挡墙/边坡/管线/高程点/土方挖填）、桩号、坐标和标高候选：

```bash
scripts/cad_scan.sh 总图.dwg --with-mtext --with-insert \
  --with-geom --with-geom-layer \
  --detail-json 总图详情.json --format json -o 总图扫描

scripts/cad_site_geometry.sh 总图详情.json --out-dir 场地识图
```

本层只做识图，不输出土方量、道路面积、管线长度汇总、材料量或造价；场地量交给市政/土建专项 skill。

## 给排水/暖通深化识图与中间数据

给排水、暖通/防排烟、消防水深化图先转成图纸类型、系统、管道/风管/设备/支吊架构件、管径/标高/编号标注和图层几何候选：

```bash
scripts/cad_scan.sh 给排水图.dwg --with-mtext --with-insert \
  --with-geom --with-geom-layer \
  --detail-json 给排水详情.json --format json -o 给排水扫描

scripts/cad_hvac_plumbing_geometry.sh 给排水详情.json --out-dir 给排水深化识图
```

本层只做识图，不展开管道长度、不计算风管面积、材料量或造价；算量交给 `anzhuang-suanliang` 或安装专项 skill。

## 精装修/室内深化、幕墙、人防、预制装配识图

同类深化识图统一由 `cad_deep_geometry` 引擎 + 各自规则包提供，覆盖精装修/室内、幕墙、人防、预制装配四类专业：

```bash
scripts/cad_interior_finish_geometry.sh  装修详情.json --out-dir 装修深化识图
scripts/cad_curtain_wall_geometry.sh     幕墙详情.json --out-dir 幕墙识图
scripts/cad_civil_defense_geometry.sh    人防详情.json --out-dir 人防识图
scripts/cad_precast_geometry.sh          预制详情.json --out-dir 预制识图
```

- 精装修/室内：地面/墙面/顶棚/踢脚/固定家具/门窗构件与做法编号、材料、标高、节点候选。
- 幕墙：玻璃/石材/金属/单元式幕墙系统，立柱/横梁/面板/开启扇/预埋件构件与分格、标高、板块编号候选。
- 人防：防护单元/人防墙/防护密闭门/防爆波活门/滤毒通风/洗消/人防电气构件与门号、抗力等级、标高候选。
- 预制装配：预制墙/叠合板/预制楼梯/预制梁柱/预埋件/连接节点构件与构件编号、桁架筋、标高候选。
- 各层只做识图证据，不输出饰面面积、排版数量、幕墙面积、板块数量、人防/预制构件数量、体积、材料量或造价。

## 结构算量的归属

原 `cad-file-reader` 内的梁、板、柱、墙、楼梯、洞口、预制底板、混凝土分账和结构算量流水线已迁移到：

- `tujian-suanliang`（本机目录 `shangwu-suanliang`）
- 统一入口：在土建算量技能目录执行其 `run_qty.sh` 命令（高级模式或流水线模式）。
- 迁移脚本仍通过 `CAD_SKILL_DIR` 调用本技能的 `cad_scan`/`cad_interpret` 识图底座。

本技能不再提供 `cad_quantity_pipeline.sh`、梁板柱墙混凝土方量、轴线面积、构件体积或材料量输出。

## 工作流

1. 识别 DWG/DXF/DWT 和大小；大图禁止直接全量实体树解析。
2. `cad_scan` 建立文字/图层/块名/图框/几何候选索引，保留原文证据。
3. 说明与规范任务运行 `cad_interpret` + `cad_normative`；装饰/安装/电气/钢结构/市政/结构/总图场地/给排水暖通/精装修幕墙人防预制识图读取对应 pack。
4. 需要算量时把识图结果交给 `tujian-suanliang`、`zhuangshi-suanliang`、`anzhuang-suanliang` 或对应专项 skill。
5. 同一张图重复查询优先复用已有 scan/detail/索引，不重复解析大图。

## 边界

- 不做设计合规审查、施工方案判断、清单计价、结算审计或规范条文解释。
- 测量候选不是最终工程量；专项算量 skill 必须继续完成扣减、重叠、做法映射、损耗、分账和台账。
- 不输出最终工程量、材料量、造价或结算量；只输出识图候选、几何证据、测量候选（`final_quantity=false`）和复核原因。
- 自动提取不能替代设计单位、翻样、清单编制和正式授权规范全文。
- 不把公司内部路径、项目结果或规范全文写入技能发布内容。

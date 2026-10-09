---
name: cad-file-reader
slug: cad-file-reader
displayName: CAD 图纸识图与证据提取
version: 0.26.5
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
- **输出深度（用户可选）**：默认完整输出；追加 `--concise` 使用精简契约省 Token（候选只保留主干字段 id/类别/图层/文本/置信度/复核原因/来源文件）；`--full` 或 `--with-evidence` 恢复完整证据。环境变量 `CAD_CONCISE=1` 可全局设为精简默认。

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

## PDF 图纸（识图候选，本机分流 + 本地 OCR）

PDF 图纸先用本机 `pdf-inspector` 分类：文本型取原生文字，扫描/混合型用 `pdftoppm` 渲染后调本地 `image-ocr` 出线性文字候选。全部结果只作识图/文字候选，一律进 `review_candidates` 并标 `missing_layer/missing_unit/missing_scale`，不输出测量数量。

扫描/混合页候选的 OCR 像素框按渲染 dpi（默认 200，1in=72pt）换算成 `page_bbox`（PDF 点），并在候选上保留 `source_bbox_px` 供追溯。

矢量 PDF（`source_format=pdf_vector`）额外输出 `pdf_meta.vector_text_items`：原生文字 `x/y/width/height/font/font_size/page` 坐标候选，单位为 PDF 点，**仅作证据与分流，不参与测量**；可单独用 `scripts/cad_pdf_vec.sh 图纸.pdf --json vec.json` 复核。

图签栏提取为**版式优先 + 关键词兜底**：`pdf_meta.title_block` 优先扫描右下角图签栏区域（x>页面宽45%、y<页面高55%）命中字段，未命中字段再回退全量关键词；`page_bbox` 记录证据坐标，仅作元数据锚点，需人工核对。

```bash
# 分类 + 输出文字识图候选（文本型 / 扫描型 PDF 均可）
scripts/cad_pdf_ocr.sh 图纸.pdf --out-dir 图纸PDF识图

# 只分类不 OCR（先看是什么类型）
scripts/cad_pdf_ocr.sh 图纸.pdf --classify-only

# 扫描页并行数（默认3，建议≤CPU核心数）
scripts/cad_pdf_ocr.sh 图纸.pdf --workers 4 --out-dir 图纸PDF识图

# 自定义缓存目录；两级缓存（文件级 pdf 元数据 + 页面级 OCR 行结果）
scripts/cad_pdf_ocr.sh 图纸.pdf --cache-dir /tmp/pdf-cache --out-dir 图纸PDF识图

# 强制重新解析/渲染，忽略缓存
scripts/cad_pdf_ocr.sh 图纸.pdf --force --out-dir 图纸PDF识图
```

输出为 `*.pdf识图.json`（cad-file-reader/v0 契约）与同名 Markdown；可用 `scripts/cad_validate.sh 输出.json` 校验。公司图纸字节全程本机处理，不上云。

## 发布预检（一条命令）

改动 Skill 后发布前跑 `scripts/run_preflight.sh`：依次执行全量 self-test、契约样例校验、`cad_release_scrub.py` 脱敏扫描；带真图清单时加 `--manifest <本地真图清单.json>` 跑真实图纸回归。任一环节失败即视为未通过，禁止发布。



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

# 省 Token：精简输出（默认完整；显式 --concise 精简候选主干，--full/--with-evidence 恢复完整）
scripts/cad_scan.sh 图纸.dwg --concise --format json -o 图纸精简

# 交付常用：同一结果同时导出 Markdown/JSON/CSV/Excel/Word
scripts/cad_scan.sh 图纸.dwg --only 梁,板,柱,墙 --cluster 1500 \
  --detail-json 图纸详情.json --format all -o 图纸扫描
# 单独导出 Excel 或 Word（需 --out 指定前缀）
scripts/cad_scan.sh 图纸.dwg --only 梁,板,柱,墙 --format xlsx -o 图纸扫描
scripts/cad_scan.sh 图纸.dwg --only 梁,板,柱,墙 --format docx -o 图纸扫描
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

## 装饰/安装/电气/钢结构/市政识图路由

专业识图统一入口见 `pack-index.md`（默认入口表）；各专业只输出识图候选，选量交给专项 skill。

| 专业 | 脚本 | 方法/边界 |
|---|---|---|
| 装饰 | `scripts/cad_descriptive_geometry.sh 详情.json --out-dir 描述几何` | `packs/descriptive-geometry/SKILL.md`；房间/洞口/做法候选，不直接出量 |
| 安装 | `scripts/cad_scan.sh 安装图.dwg ... --detail-json 安装详情.json` + `scripts/cad_mep_geometry.sh 安装详情.json` | `packs/mep-geometry/SKILL.md`；系统/路由/设备/立管候选，选量给 anzhuang-suanliang |
| 电气 | `scripts/cad_scan.sh 电气图.dwg ... --detail-json 电气详情.json` + `scripts/cad_electrical_geometry.sh` | `packs/electrical-geometry/SKILL.md`；回路/规格/防雷/消防/弱点候选；不展开芯数线长/负荷/照度 |
| 钢结构 | `scripts/cad_scan.sh 钢结构图.dwg ... --detail-json 钢结构详情.json` + `scripts/cad_steel_geometry.sh` | `packs/steel-geometry/SKILL.md`；构件/截面/连接/材料候选；重量涂装交专项 |
| 市政 | `scripts/cad_scan.sh 市政图.dwg ... --detail-json 市政详情.json` + `scripts/cad_municipal_geometry.sh` | `packs/municipal-geometry/SKILL.md`；道路/管网/桥梁/桩号/标高候选 |

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

## 结构/总图场地/给排水暖通/精装修/幕墙/人防/预制装配识图路由

| 专业 | 脚本 | 方法/边界 |
|---|---|---|
| 结构 | `scripts/cad_scan.sh 结构图.dwg ... --detail-json 结构详情.json` + `scripts/cad_structural_geometry.sh` | `packs/structural-geometry/SKILL.md`；梁板柱墙/配筋/节点/轴网候选；方量钢筋交 tujian-suanliang |
| 总图场地 | `scripts/cad_scan.sh 总图.dwg ... --detail-json 总图详情.json` + `scripts/cad_site_geometry.sh` | `packs/site-geometry/SKILL.md`；红线/道路/停车/挡墙/土方候选；量交市政/土建 |
| 给排水暖通 | `scripts/cad_scan.sh 给排水图.dwg ... --detail-json 给排水详情.json` + `scripts/cad_hvac_plumbing_geometry.sh` | `packs/hvac-plumbing-geometry/SKILL.md`；管/风管/设备/支吊架候选；量交 anzhuang-suanliang |
| 精装修/室内 | `scripts/cad_interior_finish_geometry.sh` | `packs/interior-finish-geometry/SKILL.md` |
| 幕墙 | `scripts/cad_curtain_wall_geometry.sh` | `packs/curtain-wall-geometry/SKILL.md` |
| 人防 | `scripts/cad_civil_defense_geometry.sh` | `packs/civil-defense-geometry/SKILL.md` |
| 预制装配 | `scripts/cad_precast_geometry.sh` | `packs/precast-geometry/SKILL.md` |

各专业只做识图证据，不输出面积/长度/数量/体积/材料量或造价；统一契约与置信度分层见上文“统一候选契约”。本机真实回归用 `scripts/run_real_dwg_regression.sh --manifest 真图清单.json`，清单可写 `kind=electrical|structural|site|hvac_plumbing|interior_finish|curtain_wall|civil_defense|precast`，发布前脱敏。

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

# CAD 图纸识图与证据提取（cad-file-reader）

> 📦 **SkillHub 安装**：`skillhub install cad-file-reader`　|　仓库：[lisong2003-lgtm/cad-file-reader](https://github.com/lisong2003-lgtm/cad-file-reader)


一个给 AI 编码助手使用的本地 CAD **识图与证据提取** Skill。直接解析 DWG/DXF/DWT，不需要安装 AutoCAD。适合大图快速扫描、图层/文字/块/图框索引、建筑/结构/MEP/钢结构/市政识图候选、规范图集引用定位和回图复核。

> 定位：识图与证据工具，不替代设计审查、清单计价、翻样下料、结算或规范条文解释。
> 身份透明：这是 AI 助手调用的工具型 Skill，不伪装成任何人物或外部产品。

## 0.24.0 新增概览

新增**纵深专业识图引擎与 5 个深化识图包**（`cad_deep_geometry.py` + `packs/`）：

- 给排水/暖通深化（`hvac-plumbing-geometry`）：给水/排水/消防水/暖通/防排烟/泵房/支吊架图纸类型与系统，管道、风管、风机盘管/风口/设备、支吊架构件，管径（DN/De/D）、标高、设备/立管编号候选。
- 精装修/室内深化（`interior-finish-geometry`）：装修平面/立面/节点/做法表/门窗表/固定家具，地面/墙面/顶棚/踢脚/家具/防水构件，做法编号/材料/标高/节点候选。
- 幕墙（`curtain-wall-geometry`）：玻璃/石材/金属/单元式幕墙，立柱/横梁/面板/开启/预埋件/胶条构件，分格/标高/板块/预埋编号候选。
- 人防（`civil-defense-geometry`）：防护单元/人防墙/防护密闭门/防爆波活门/滤毒通风/洗消/人防电气，门号/抗力等级/标高/设备编号候选。
- 预制装配（`precast-geometry`）：预制墙/叠合板/预制楼梯/预制梁柱/预埋件/连接节点，构件编号/桁架筋/标高/预埋编号候选。
- 统一按 `cad_scan` 详情输入，输出 `*.<pack>.json/md/csv` 与 `cad-file-reader/v0` contract，固定 `final_quantity=false`；缺几何/缺比例/单位/图层未分类/标注未绑定进入复核。
- 新增 5 组合成回归；完整自测 87 项通过。真图回归（结构/总图/给排水喷淋/人防/精装修）5/5 pass；幕墙（会展2#立面/LM）与预制装配（安置五装配式改铝膜结构）真图接入后 7/7 pass。
- 发布前脱敏自检通过（63 文件 0 命中）。完整清单见 `CHANGELOG.md`。

## 0.23.0 新增概览

新增**结构识图候选包**（`packs/structural-geometry`）和**总图/场地识图候选包**（`packs/site-geometry`）：

- 结构：识别结构平面/配筋/基础/楼梯/节点等图纸类型，梁/板/柱/墙/基础/楼梯/洞口构件，HPB300/HRB400 等配筋标注，KL/KZ/YBZ 等编号，节点/轴网候选；只做识图证据，不换算混凝土方量/钢筋吨位/锚固长度。
- 总图/场地：识别总平面、竖向设计、管线综合、道路纵横断面、挡土墙/边坡、停车、景观图纸与系统，红线/道路/停车位/挡墙/护坡/管线/高程点/土方挖填等场地构件候选，以及桩号、坐标、标高标注；只做识图证据，不输出土方量、道路面积或管线长度汇总。
- 新增 `scripts/cad_structural_geometry.sh`、`scripts/cad_structural_geometry.py` 与 `scripts/cad_site_geometry.sh`、`scripts/cad_site_geometry.py`，输出 `*_structural.json/md/csv` 和 `*_site.json/md/csv`，统一候选契约固定 `final_quantity=false`。
- 真实回归：本轮已接入本机知识库结构 DWG 和总平面 DWG 回归，`run_real_dwg_regression.sh` 清单支持 `kind=electrical|structural|site`。）

## 0.22.0 新增概览

继续强化电气识图：新增消防（消防水/喷淋/气体灭火/防排烟/防火卷帘/消防联动/消防泵）、弱点/弱电（综合布线/CCTV/门禁/广播）和智能化（BAS/能耗计量/智能照明/IBMS）三个领域映射；新增消防水/喷淋、消防联动、防排烟、气体灭火、智能化、综合布线、CCTV、广播平面等图纸类型，消防火警环路与弱电信号总线路由，防火卷帘/消防泵/排烟口/网络设备/摄像机/门禁/广播音箱/DDC/能耗表/智能照明面板等设备，以及 UTP/STP/CAT5E/CAT6/GYXTW/GYTA/FIBER 规格和 FAS/FA/FBF/FB/FBN/CCTV/PDS/ACS/PA/AV/IBMS/BMS 回路前缀；JSON/MD/CSV 增加 `fire_protection`、`weak_current`、`intelligent_building` 领域分组字段。完整清单见 `CHANGELOG.md`。

## 0.21.0 新增概览

新增电气专业识图中间数据：`cad_electrical_geometry.sh` 输出变配电/照明/动力/应急/火灾报警/安防/弱电/防雷接地图纸类型、系统、桥架/母线/导管/电缆路由、配电箱/柜、灯具、开关插座、探测器、回路编号与规格标注、防雷接地候选和证据坐标；只做识图候选，不展开芯数/线长、不做负荷/照度/母排计算，不输出材料量或结算量。新增本机真实 DWG 回归入口 `scripts/run_real_dwg_regression.sh --manifest <本地真图清单>`，用知识库消防/弱电/智能化真图验证领域候选；真图清单放在技能包之外，发布内容不包含公司图纸路径。完整清单见 `CHANGELOG.md`。

## 0.20.1 新增概览

本版本汇聚并修复 P0–P5 优化：P0 统一候选契约与置信度分层、P1 大图缓存与局部解析、P2/P3 图层/块语义、P4 MEP 拓扑增强、P5 图纸对比；并修复 SkillHub 轻量包自动下载完整依赖。

- **修复**：SkillHub 轻量包 `scripts/install_vendor.sh` 现在兼容 `cad-file-reader-full-<ver>.zip` 和 `cad-file-reader-<ver>-full.zip` 两种 Release 命名，可自动下载同版本 vendor。
- **公共模块与启动器收敛**：新增 `scripts/cad_common.py`，统一跨脚本公共函数；semantics/compare 启动器改用 `run_cad.sh`。
- **统一候选契约 P0**：识图与测量 JSON 额外输出 `contract`，分 `confirmed_evidence`、`inferred_candidate` 和 `review_required`；标准复核原因写入 `review_reasons[]`，中文说明保留在 `review_notes`。低置信和阻断项不进入默认汇总主线。
- **交接校验**：用 `scripts/cad_validate.sh 输出.json` 校验候选字段、置信度分层、复核原因和 `final_quantity=false` 边界。
- **大图缓存 P1**：同图重复查询可复用本机证据缓存；支持按图面矩形 `--roi` 或图框编号 `--sheet` 局部读取。
- **图层/块语义 P2/P3**：新增 `cad_semantics.sh`，从 `cad_scan` 详情 JSON 输出图层语义、块语义和块实例关联候选；支持层数、块数、实例数和关联半径上限。无语义、匿名块、缺块定义或低置信关联只进入复核。
- **MEP 拓扑增强 P4**：`cad_mep_geometry.sh` 新增 `mep_relations`，输出设备—管段、立管—管段、端点连接和系统冲突候选；缺图层、缺系统、几何冲突或距离异常进入复核。
- **图纸对比 P5**：新增 `cad_compare.sh`，对比基准/目标详情 JSON 的图层、块、文字、几何增删与移动；输出 `drawing_changes`，不解释工程量增减。
- **测量候选层**：`cad_measure.sh` 输出长度、面积、体积识图候选，每条固定 `final_quantity=false`。
- **边界**：本技能不计算最终工程量、材料量、造价或结算量；口径、扣减、损耗、分账和台账交给专项算量 skill。

## 能力

- DWG/DXF/DWT 直接读取；支持单文件、目录和递归扫描。
- 低内存快速路径：文字、图层、块名、关键词、构件编号、图框和几何候选。
- 说明解释与规范引用初解：`cad_interpret.sh`；规范/图集元数据辅助：`cad_normative.sh`。
- 装饰识图中间数据：`cad_descriptive_geometry.sh`，输出房间边界、墙段分段、顶棚分区、楼梯/坡道/台阶初稿、外墙分格/保温分区、门窗、做法、节点索引和证据坐标。
- 测量候选：`cad_measure.sh`，把上述识图 JSON 转成可追溯的长度/面积/体积候选，保留图面值、比例、单位、计算式和复核原因。
- 图例知识表候选：`cad_legend.sh`，按轻量图例词库匹配块名/图层/文字关键词，输出专业/语义/命中词和 `discipline_refs`；不引视觉模型。
- 图层/块语义：`cad_semantics.sh`，输出图层语义、块语义和块实例关联候选；上限可控，低置信项单独复核。
- 安装识图中间数据：`cad_mep_geometry.sh`，输出安装图纸类型、专业系统、路由段、设备、标注、立管、竖向路由、系统拓扑、MEP 关联候选和证据坐标。
- 电气识图中间数据：`cad_electrical_geometry.sh`，输出变配电/照明/动力/应急/火灾报警/消防（消防水/喷淋/气体灭火/防排烟/防火卷帘/消防联动/消防泵）/安防/弱点/弱电（综合布线/CCTV/门禁/广播）/智能化（BAS/能耗计量/智能照明/IBMS）/防雷接地图纸类型、系统、桥架/母线/导管/电缆路由段、消防火警环路/弱电信号总线、配电箱/柜、灯具、开关插座、探测器、消防/弱电/智能化设备、回路编号、规格标注、防雷接地候选、领域分组和证据坐标。
- 图纸对比：`cad_compare.sh`，输出图层、块、文字和几何的增删/移动候选；不解释工程量变化。
- 给排水/暖通深化识图：`cad_hvac_plumbing_geometry.sh`，输出给水/排水/消防水/暖通/防排烟/支吊架图纸类型、系统、管道/风管/设备/支吊架构件、管径/标高/编号标注候选。
- 精装修/室内深化识图：`cad_interior_finish_geometry.sh`，输出装修图纸类型、系统、地面/墙面/顶棚/踢脚/家具/防水构件、做法编号/材料/标高/节点候选。
- 幕墙专业识图：`cad_curtain_wall_geometry.sh`，输出幕墙图纸类型、系统、立柱/横梁/面板/开启/预埋件/胶条构件、分格/标高/板块/预埋编号候选。
- 人防工程识图：`cad_civil_defense_geometry.sh`，输出人防图纸类型、系统、防护设备/门/通风/电气/洗消构件、门号/抗力等级/标高候选。
- 预制装配深化识图：`cad_precast_geometry.sh`，输出预制图纸类型、系统、预制构件/预埋件/连接节点、构件编号/桁架筋/标高候选。
- 结构识图与中间数据：`cad_structural_geometry.sh`，输出结构图纸类型、结构系统、梁/板/柱/墙/基础/楼梯/洞口构件、配筋标注、结构编号、节点、轴网和几何候选；只做识图证据，不换算混凝土方量/钢筋吨位。
- 总图/场地识图与中间数据：`cad_site_geometry.sh`，输出总平面/竖向/管线综合/道路/挡墙边坡/停车/景观图纸类型、系统、场地构件、桩号、坐标、标高和几何候选；只做识图证据，不输出土方量、面积或管线长度汇总。
- 钢结构识图中间数据：`cad_steel_geometry.sh`，输出钢结构图纸类型、结构系统、构件、截面、连接、材料、涂装、节点、轴网/标高、几何和连通性候选。
- 市政专业识图中间数据：`cad_municipal_geometry.sh`，输出市政图纸类型、专业系统、道路/桥隧/管网构件、材料、桩号、标高、坐标、几何和连通性候选。
- 输出 Markdown / JSON / CSV；重要识图流水线可生成 manifest 和 SHA-256。
- 大图证据缓存：SQLite 单文件按源文件 SHA-256 + 扫描参数档隔离；支持 ROI 和图框局部读取，并输出命中/未命中统计。
- 缓存治理：`cad_cache_admin.sh` 盘点 current/legacy/temp/corrupt/unknown；默认只读，清理默认 dry-run。
- 统一候选契约：`cad-file-reader/v0`；`candidates[]` 不含 `review_required`，复核项单独放 `review_candidates[]`，可用 `scripts/cad_validate.sh` 校验。

## 安装

### GitHub 完整包

完整包已内置 `vendor/`。解压后复制到技能目录：

```bash
cp -R cad-file-reader "$CODEX_HOME/skills/"
```

需要 Python 3.10+；普通 Python 环境缺少 numpy 时安装：

```bash
python3 -m pip install numpy
```

### SkillHub 轻量包

轻量包是纯文本合规包，不含 `vendor/` 二进制。安装后执行一次：

```bash
cd "$CODEX_HOME/skills/cad-file-reader"
scripts/install_vendor.sh
```

安装后功能与完整包一致。

## 快速使用

```bash
# 大图优先：低内存扫描
scripts/cad_scan.sh 图纸.dwg --only 梁,板,柱,墙 --cluster 1500 --format md -o 图纸扫描

# 说明、规范引用和参数候选
scripts/cad_scan.sh 图纸.dwg --with-mtext --with-geom \
  --detail-json 图纸详情.json --format json -o 图纸扫描
scripts/cad_interpret.sh --scan 图纸扫描.json --detail 图纸详情.json \
  --rules rules --format all -o 图纸解读
scripts/cad_normative.sh --scan 图纸扫描.json --detail 图纸详情.json \
  --rules rules --format all -o 规范辅助

# 测量候选（长度/面积/体积）
scripts/cad_measure.sh 描述几何/图纸详情.descriptive.json --out-dir 测量候选
# 缺比例/单位时保留图面值并转 review；只有 paper/layout 空间才应用图框比例
scripts/cad_measure.sh 安装识图/安装详情.mep.json --scale 1:100 --unit mm --coordinate-space model --out-dir 测量候选

# 图层/块语义候选
scripts/cad_semantics.sh 图纸详情.json --out-dir 语义识图 \
  --max-layers 2000 --max-blocks 2000 --max-instances 2000 --link-radius 3000

# 安装识图与 MEP 关联
scripts/cad_scan.sh 安装图.dwg --with-mtext --with-insert \
  --with-geom --with-geom-layer --detail-json 安装详情.json --format json -o 安装扫描
scripts/cad_mep_geometry.sh 安装详情.json --out-dir 安装识图

# 电气识图
scripts/cad_scan.sh 电气图.dwg --with-mtext --with-insert \
  --with-geom --with-geom-layer --detail-json 电气详情.json --format json -o 电气扫描
scripts/cad_electrical_geometry.sh 电气详情.json --out-dir 电气识图


# 图纸对比
scripts/cad_compare.sh 基准详情.json 目标详情.json \
  --out-dir 图纸对比 --tolerance 1.0 --max-changes 5000

# 结构算量入口已迁到土建算量 skill
cd "$CODEX_HOME/skills/shangwu-suanliang"
土建算量技能目录执行 `run_qty.sh advanced 结构图.dwg --out 首层算量`
```

## 大图缓存与局部解析

```bash
# 首次全量扫描并建立本机证据缓存
scripts/cad_scan.sh 图纸.dwg --with-geom --with-geom-layer \
  --cache-dir /tmp/cad-file-reader-cache --format all -o 图纸扫描

# 同图重复查询：按图面矩形局部读取
scripts/cad_scan.sh 图纸.dwg --with-geom --with-geom-layer \
  --cache-dir /tmp/cad-file-reader-cache --roi 0,0,30000,20000 --format json -o 局部读取

# 同图重复查询：按图框编号局部读取
scripts/cad_scan.sh 图纸.dwg --with-geom --with-geom-layer \
  --cache-dir /tmp/cad-file-reader-cache --sheet 1 --format json -o 图框读取
```

- 缓存键使用源文件 SHA-256 和影响证据内容的扫描参数档；源图或参数变化不会误命中。
- `--roi left,bottom,right,top` 与 `--sheet 图框编号` 只做查询过滤，不进入缓存键。
- JSON 输出 `cache.dir/hits/misses`，每个文件带 `cache=hit|miss`。
- 局部结果只返回命中范围内的证据；不携带整图块统计。
- ROI 几何过滤使用预归一化 bbox 索引；缓存写入采用批量落库、延后建索引和原子替换。
- JSON 汇总带 `cache.read_ms/write_ms/db_files/db_bytes`；每个文件带 `cache_read_ms/cache_write_ms/cache_bytes`。
- 缓存治理：

```bash
# 默认只读盘点
scripts/cad_cache_admin.sh /tmp/cad-file-reader-cache

# 生成清理计划：默认只处理 temp/legacy，不删除
scripts/cad_cache_admin.sh /tmp/cad-file-reader-cache --cleanup

# 实际删除计划内文件
scripts/cad_cache_admin.sh /tmp/cad-file-reader-cache --cleanup --apply

# 清 current 必须显式开启，且提供年龄或容量上限
scripts/cad_cache_admin.sh /tmp/cad-file-reader-cache --cleanup --apply \
  --include-current --max-age-days 30
```

- `corrupt` 和 `unknown` 只报告，永不删除；`current` 默认保留。
- 缓存目录建议放本机临时目录或用户指定本机目录；公司图纸不上传。
- 缓存只复用识图证据，不改变 `final_quantity=false` 边界。

## 边界

- 不做设计合规审查、施工方案判断、清单计价、结算审计或规范条文解释。
- 测量候选固定 `final_quantity=false`；不输出最终工程量、材料量、造价或结算量。
- 规范/图集辅助只提供元数据、版本风险和资料入口；适用性以图纸指定版本和授权全文为准。
- 大图优先低内存扫描；高内存/高 CPU 时应暂停，不应盲目全量解析。
- 公司项目路径、内部结果和规范全文不得进入技能发布内容。

## 许可

本包文档与脚本采用 CC BY-NC-SA 4.0。第三方解析库许可见 `NOTICE.md`。

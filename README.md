# CAD 图纸识图与证据提取（cad-file-reader）

一个给 AI 编码助手使用的本地 CAD **识图与证据提取** Skill。直接解析 DWG/DXF/DWT，不需要安装 AutoCAD。适合大图快速扫描、图层/文字/块/图框索引、建筑/结构/MEP/钢结构/市政识图候选、规范图集引用定位和回图复核。

> 定位：识图与证据工具，不替代设计审查、清单计价、翻样下料、结算或规范条文解释。
> 身份透明：这是 AI 助手调用的工具型 Skill，不伪装成任何人物或外部产品。

## 0.18.0 新增概览

- **测量候选层**：新增 `cad_measure.sh`，可输出长度、面积、体积的识图候选值、计算式、比例单位依据和证据；每条固定 `final_quantity=false`。
- **职责收口**：`cad-file-reader` 只保留识图、几何候选、测量候选、证据和复核边界，不输出最终工程量、材料量、造价或结算量。
- **算量迁移**：原梁板柱墙、楼梯、洞口、预制底板、混凝土分账和结构算量流水线迁到 `tujian-suanliang`（本机目录 `shangwu-suanliang`）。
- **入口清理**：删除 `cad_quantity_pipeline.sh`、`--axis-grid`、`--thk-mm`、`--col-height-mm`、混凝土 CSV/Markdown 和楼层梁混凝土初算输出。
- **底座保留**：`cad_scan`/`cad_interpret` 仍保留文字、图层、图框、几何线段、构件标注、净跨/支座候选和原文证据，供各专项算量 skill 调用。
- **边界**：本技能不计算最终量；测量候选不能直接当清单量或结算量，算量 skill 负责口径、扣减、损耗、分账和台账。

## 能力

- DWG/DXF/DWT 直接读取；支持单文件、目录和递归扫描。
- 低内存快速路径：文字、图层、块名、关键词、构件编号、图框和几何候选。
- 说明解释与规范引用初解：`cad_interpret.sh`；规范/图集元数据辅助：`cad_normative.sh`。
- 装饰识图中间数据：`cad_descriptive_geometry.sh`，输出房间边界、墙段分段、顶棚分区、楼梯/坡道/台阶初稿、外墙分格/保温分区、门窗、做法、节点索引和证据坐标。
- 测量候选：`cad_measure.sh`，把上述识图 JSON 转成可追溯的长度/面积/体积候选，保留图面值、比例、单位、计算式和复核原因。
- 安装识图中间数据：`cad_mep_geometry.sh`，输出安装图纸类型、专业系统、路由段、设备、标注、立管、竖向路由、系统拓扑候选和证据坐标。
- 钢结构识图中间数据：`cad_steel_geometry.sh`，输出钢结构图纸类型、结构系统、构件、截面、连接、材料、涂装、节点、轴网/标高、几何和连通性候选。
- 市政专业识图中间数据：`cad_municipal_geometry.sh`，输出市政图纸类型、专业系统、道路/桥隧/管网构件、材料、桩号、标高、坐标、几何和连通性候选。
- 输出 Markdown / JSON / CSV；重要识图流水线可生成 manifest 和 SHA-256。

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

# 安装识图中间数据
scripts/cad_scan.sh 安装图.dwg --with-mtext --with-insert \
  --with-geom --with-geom-layer --detail-json 安装详情.json --format json -o 安装扫描
scripts/cad_mep_geometry.sh 安装详情.json --out-dir 安装识图

# 结构算量入口已迁到土建算量 skill
cd "$CODEX_HOME/skills/shangwu-suanliang"
scripts/run_qty.sh advanced 结构图.dwg --floor-label "二层梁平法施工图" --out 首层算量
```

## 边界

- 不做设计合规审查、施工方案判断、清单计价、结算审计或规范条文解释。
- 测量候选固定 `final_quantity=false`；不输出最终工程量、材料量、造价或结算量。
- 规范/图集辅助只提供元数据、版本风险和资料入口；适用性以图纸指定版本和授权全文为准。
- 大图优先低内存扫描；高内存/高 CPU 时应暂停，不应盲目全量解析。
- 公司项目路径、内部结果和规范全文不得进入技能发布内容。

## 许可

本包文档与脚本采用 CC BY-NC-SA 4.0。第三方解析库许可见 `NOTICE.md`。

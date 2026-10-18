# CAD 图纸识图与证据提取（cad-file-reader）

本地运行的 CAD **识图与证据提取** Skill：直接解析 DWG/DXF/DWT 与 PDF 图纸，不需要 AutoCAD，全部本机处理、图纸字节不上传。

定位：识图与证据工具，不替代设计审查、清单计价、翻样下料、结算或规范条文解释。
身份透明：这是 AI 助手调用的工具型 Skill，不伪装成任何人物或外部产品。

## 能做什么

- **流式解析** DWG/DXF/DWT：图层、文字、块、图框、几何、构件编号、关键词。
- **专业识图候选**（17 个专业包）：建筑、结构、总图场地、安装、电气（含消防/弱点/智能化）、钢结构、市政、给排水暖通、精装修、幕墙、人防、预制装配、桥梁隧道道路、桩基基坑边坡、门窗楼梯保温防水、防火无障碍绿建。
- **园林景观识图**：苗木图例/乔灌地被候选、铺装闭合域轻量候选、设计院图例快速校准、DWG 块名净化与 `--dwg-dxf-fallback` 自动转 DXF 复扫；全部 `final_quantity=false`。
- **长度/面积/体积测量候选**：每条 `final_quantity=false`，不冒充工程量。
- **规范/图集元数据定位**、图层/块语义、图纸变化对比、PDF 识图（本机类型分流 + 本地 OCR）。
- **大图低内存扫描**、证据缓存、局部解析；Markdown / JSON / CSV / Excel / Word 输出。
- **统一候选契约** `cad-file-reader/v0`：证据坐标、置信度分层（confirmed/inferred/review）、复核原因。

## 安装

依赖：Python 3.10+；解析库随完整包自带，或由轻量包一条命令补齐。

完整包（已内置 vendor）：

```bash
cp -R cad-file-reader "$CODEX_HOME/skills/"
# 可选：普通环境缺 numpy 时
python3 -m pip install numpy
```

SkillHub 轻量包（纯文本合规包，不含二进制 vendor）：

```bash
cd "$CODEX_HOME/skills/cad-file-reader"
scripts/install_vendor.sh   # 一条命令自动补齐依赖
```

装好后自检（一条命令看哪些能力可用/缺依赖）：

```bash
scripts/deps_check.sh --minimal
```

## 快速开始（30 秒见结果）

```bash
scripts/demo.sh                       # 用内置样例 DXF 跑一次完整识图，展示首屏 JSON
scripts/cad_scan.sh 图纸.dwg --only 梁,板,柱,墙 --cluster 1500 --format md -o 图纸扫描
scripts/cad_scan.sh 图纸.dwg --with-mtext --with-geom --detail-json 详情.json --format all -o 图纸扫描
scripts/cad_measure.sh 详情.json --out-dir 测量候选
```

## 使用指引

- 全部命令入口与专业路由见 `pack-index.md`（默认入口表）。
- 能力边界矩阵见 `CAPABILITIES.md`。
- 版本变更见 `CHANGELOG.md`。

## 边界

- 只输出识图、证据、语义/拓扑/变化候选和测量候选（固定 `final_quantity=false`）。
- 不做设计合规审查、清单计价、结算审计或规范条文解释。
- 不输出最终工程量、材料量、造价或结算量。
- 自动提取不能替代设计单位、翻样、清单编制和正式授权规范全文。
- 算量交给专项 skill（土建 → tujian-suanliang，装饰/安装 → 对应专项）。
- 公司项目路径、内部结果和规范全文不得进入技能发布内容。

## 许可

本包文档与脚本采用 CC BY-NC-SA 4.0。第三方解析库许可见 `NOTICE.md`。

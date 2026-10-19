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
bash scripts/install_vendor.sh   # 默认零配置：自动用公共 PyPI 补齐依赖到本包 vendor/
```

装好后自检（一条命令看哪些能力可用/缺依赖）：

```bash
bash scripts/deps_check.sh --minimal
```

## 快速开始（30 秒见结果）

```bash
bash scripts/demo.sh                       # 用内置样例 DXF 跑一次完整识图，展示首屏 JSON
scripts/cad_scan.sh 图纸.dwg --only 梁,板,柱,墙 --cluster 1500 --format md -o 图纸扫描
scripts/cad_scan.sh 图纸.dwg --with-mtext --with-geom --detail-json 详情.json --format all -o 图纸扫描
scripts/cad_measure.sh 详情.json --out-dir 测量候选
```

SkillHub 轻量包不含 `.dxf` 样例，`scripts/demo.sh` 会用 `scripts/generate_sample.py` 现场还原内置样例后继续。

## 五件套联动端到端示例（qto-project/v1）

在同一个项目目录里跑「识别 → P1 → P2 → P3 → 校验」，**不要求五件全装**；缺专业会占位，不阻断体系。

```bash
# 1) 建联动项目，--recognized 支持一次多个量算专业（已识别/要接入的）
SKILL_DIR/cad-file-reader/scripts/qto_project.py init 项目A \
  --project 示例项目 --building 1#楼 \
  --recognized tujian-suanliang anzhuang-suanliang zhuangshi-suanliang yuanlin-suanliang

# 2) 把你的识图结果包装进各专业识别层（base + 各量算专业）
SKILL_DIR/cad-file-reader/scripts/qto_project.py wrap 1#楼识图.json \
  --specialty cad-file-reader --project 示例项目 --building 1#楼 \
  --out 项目A/识别/cad-file-reader/1#楼__cad-file-reader__20261019.json
# …量算专业同理（--specialty tujian-suanliang / …）

# 缺识图但已登记的专业可补占位：
SKILL_DIR/cad-file-reader/scripts/qto_project.py placeholder 项目A \
  --specialty zhuangshi-suanliang --project 示例项目 --note "本轮未出图，待装饰识图"

# 3) P1 算量联动登记：有既有量算结果用 --quantity 附着（仅登记，final_quantity=false）
SKILL_DIR/cad-file-reader/scripts/qto_p1_link.py --project-dir 项目A \
  --specialty tujian-suanliang --quantity 土建量算.json --draft-type 物资计划
SKILL_DIR/cad-file-reader/scripts/qto_p1_link.py --project-dir 项目A --specialty anzhuang-suanliang

# 4) P2 汇总 + P3 交叉核对
SKILL_DIR/cad-file-reader/scripts/qto_p2_summarize.sh --project-dir 项目A
SKILL_DIR/cad-file-reader/scripts/qto_p3_clash.sh --project-dir 项目A

# 5) 项目级校验：qto 契约 + 识别层完整性 + regression_pass/precision_note 分开统计
SKILL_DIR/cad-file-reader/scripts/qto_validate.sh 项目A --report-json 项目A/validate-report.json
```

产物落在：`.qto/project.yaml`、`识别/<专业slug>/`、`算量/<专业slug>/`、`汇总/<key>__汇总__<date>.json|csv`、`汇总/<key>__交叉核对__<date>.json|csv`。全链路只登记与汇总，不计算最终工程量。

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

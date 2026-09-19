# CAD File Reader

一个给 AI 编码助手使用的本地 CAD 读取与工程量辅助 Skill。直接解析 DWG/DXF/DWT，
不需要安装 AutoCAD。适合大图快速扫描、构件统计、结构算量流水线、规范/图集引用定位，
以及需要证据和复核边界的混凝土量台账。

> 定位：自动读图与计划口径辅助工具；不替代设计审查、清单计价、翻样下料、结算或规范条文解释。
> 身份透明：这是 AI 助手调用的工具型 Skill，不伪装成任何人物或外部产品。

## 0.5.0 优化概览

- **规范/图集辅助**：`cad_normative.sh` 识别图纸引用的规范/图集编号，匹配 54 条元数据，
  其中 46 条给出知识库相对入口。输出现行/旧版/待确认/未索引状态，并提示缺少设计输入。
- **口径冲突提示**：不同图框或说明给出同一参数不同值时，标为冲突并要求绑定部位复核。
- **编号别名匹配**：支持 `GB/T50001-2017` 与 `GBT50001-2017`、基础编号与年版编号。
- **Token 架构优化**：主入口保持短路由；算量长流程外移到专用包，按需读取。
  主入口约 7.5 KB，旧算量说明约 105 KB 精简到约 2 KB。
- **证据与边界不变**：自动提取保留原文证据；规范辅助只定位资料入口和版本风险，不输出合规结论。

## 能力

- DWG / DXF / DWT 直接读取；支持单文件、目录和递归扫描。
- 低内存快速路径：文字、图层、块名、关键词、构件编号、图框。
- 说明解释与规范引用初解：`cad_interpret.sh`。
- 规范/图集元数据辅助：`cad_normative.sh`。
- 结构几何与混凝土算量流水线：`cad_quantity_pipeline.sh`，输出候选量、风险量、正式入账口径分层。
- 按楼层/图框取数，支持全量文字/图层/坐标台账。
- DWG→DXF 转换；小图可用全量实体树和 SVG 预览。
- Markdown / JSON / CSV 输出；重要流水线带 SHA-256。

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

# 结构算量流水线
scripts/cad_quantity_pipeline.sh 结构图.dwg \
  --floor-label "二层梁平法施工图" \
  --support-floor-label "标高X~Y墙柱平法施工图" \
  --slab-floor-label "二层板结构施工图" \
  --out 首层算量
```

## 边界

- 不做设计合规审查、施工方案判断、清单计价、结算审计或规范条文解释。
- 规范/图集辅助只提供元数据、版本风险和资料入口；适用性以图纸指定版本和授权全文为准。
- 数量分为候选量、复核量和正式入账口径；缺输入记为缺口，不自动编造。
- 大图优先低内存扫描；高内存/高 CPU 时应暂停，不应盲目全量解析。

## 许可

本包文档与脚本采用 CC BY-NC-SA 4.0。第三方解析库许可见 `NOTICE.md`。

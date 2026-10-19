# 更新记录
# 更新记录
## 0.31.2 — 2026-10-19（安全优化：消除动态代码执行信号）

- `scripts/cad_interpret.py` 的 `safe_eval_expression` 由 `eval(compile(...))` 改为纯 AST 解释器 `_eval_rule_node`：保留原有白名单校验（节点类型 + 变量名），行为与原实现等价（算术/比较/布尔/三元/仅白名单函数调用），不再触发 ClawHub 静态扫描 `suspicious.dynamic_code_execution`。
- 新增 `SafeEvalExpressionTest` 4 项：等价性 + 拒绝任意代码（`__import__`/属性/下标/推导式/未知变量）。全量自测 181 → 185。
## 0.31.1 — 2026-10-19（融合线上 SkillHub 0.28.22 平台可用性 + 本机 0.31.0 五件套联动）

- 以线上 SkillHub 0.28.22 为基础合并：`setup.sh / demo.sh / install_vendor.sh / ensure_runtime.sh / run_cad.sh` 统一 `bash 前缀调用` 并在启动时自动补回下载包可执行位（`chmod +x scripts/*.sh`），修复 SkillHub zip 解压后 `Permission denied`。
- `install_vendor.sh` 恢复默认零配置：未设置 `CAD_FILE_READER_REPO` 时用公共 PyPI 补齐 ezdwg/ezdxf/fonttools/pyparsing/numpy；设置后优先走 GitHub Release 完整包 + SHA-256，失败回退公共 PyPI。
- `demo.sh` 保留在线版可用性：完整包用 `examples/sample_room.dxf`，SkillHub 轻量包缺样例时由 `scripts/generate_sample.py`（base64 内嵌同一样例）现场重建后再跑识图→测量→契约校验。
- 保留 `packs/landscape-geometry/institutes/institute_sample.json`（平台通用样例院所词库）与本机 `jingyilu.json`（真实院所词库）并存，运行时按文件存在性加载。
- 保留本机 0.29.0–0.31.0 全部 qto-project/v1 五件套联动（P0 契约 / P1 登记 / P2 汇总 / P3 交叉核对）与真实园林校准词（槐荫/分局/公安局等）；本地默认继续以真实词库为准，平台发布可换用通用样例词库。
- `run_preflight.sh` 融合两侧：SkillHub 合规扫描保留，命令调用统一 `bash` 前缀并自动补可执行位。
## 0.31.0 — 2026-10-19（五件套联动体系 P3：跨专业交叉核对）

- 新增 `scripts/qto_p3_clash.py`（+ `.sh` 入口）：按部位聚合算量登记，同部位多专业有输出 → 生成 `cross_checks` 需人工交叉核对清单；输出 `汇总/<key>__交叉核对__<date>.json` + `.csv`。
- 覆盖信号：`missing`（已登记 active 但缺算量）/ `not_installed` / `gap`（缺识别）；仅汇总状态与缺口，不计算量、不仲裁量值（最终工程量仍以各专业复核为准）。
- 新增 `scripts/tests/test_qto_p3_clash.py`（2 项）；全量自测 179→181。
- 自检修复：`qto init --recognized` 现支持重复传/一次多值（argparse append）；发布脱敏测试工程名由“示例工程”改为通用“示例工程”。

## 0.30.0 — 2026-10-19（五件套联动体系 P2：汇总层）

- 新增 `scripts/qto_p2_summarize.py`（+ `.sh` 入口）：读 `算量/<专业>/*.json` 与 `.qto/project.yaml`，生成 `汇总/<key>__汇总__<date>.json` 与 `.csv`。
- 状态口径：`ok` / `pending` / `gap` / `not_installed` / `missing`；汇总 `totals` 含候选总数与需核对总数。
- 只汇总不计算量：不做跨专业仲裁（P3），不生成最终工程量；固件不改四算量算法（P0/P1 边界延续）。
- 新增 `scripts/tests/test_qto_p2_summarize.py`（2 项）；全量自测 177→179。

## 0.29.1 — 2026-10-19（五件套联动体系 P1：算量联动适配器）

- 新增 `scripts/qto_p1_link.py`：从 `识别/<slug>/` 读识图候选 → 写 `算量/<slug>/`；缺识别写 `recognition_missing` 缺口占位（`status=gap`、rc=0，不阻断体系）；有 `--quantity` 附着既有量算结果但恒 `final_quantity=false`+`review_required=true`。
- 缺识别/待专业量算均登记为占位，不执行算量算法、不解析大 DWG、不改四算量既有算法与口径。
- 新增 `scripts/tests/test_qto_p1_link.py`（4 项：单专业/多专业/缺口/附着复核），全量自测 173→177。
- 四算量 `SKILL.md`+`CHANGELOG.md` 各加 P1 目录级联动说明（仅文档，不变算法/版本）。


## 0.29.0 — 2026-10-19（五件套联动体系 P0：qto-project/v1 契约落地）
- 新增 `qto-project/v1` 联动契约（只放底座，向后兼容 `cad-file-reader/v0`）：顶层追加可选字段 `qto_spec`、`project_key`（工程/楼栋/楼层/分区/房间/专业/source/review_required 三级来源）、`draft_type`（概算|物资计划|draft_type_pending）、`specialty`、`producer`、`placeholder`；旧 v0 字段/语义零改动。
- 新增项目目录约定：`.qto/project.yaml`、`识别/<专业slug>/`、`算量/<专业>/`（P1）、`汇总/`（P2）；未装专业登记 `not_installed` 并放占位 JSON，汇总只出占位不报错。
- 新增 `scripts/qto_project.py`（init/wrap/placeholder 生成工具）、`scripts/qto_validate.sh`（项目目录校验器）、`schemas/qto-project-v1.schema.json`、`rules/skills-map.json`、`docs/qto-linkage.md`。
- 校验口径分离：`regression_pass`（v0/cad 契约全通过）与 `precision_note`（P0/P2/P3 需人工核对清单）分开统计；旧 v0 输出只 warning 不 fail。
- 新增 `scripts/tests/test_qto_project.py` 6 项；全量自测 167→173 通过；自绘简化样本 `examples/qto-sample/`（示例楼）校验通过（1 真输出 + 4 占位）。
- 发布合规：公开样例一律自绘，不放置真实项目路径/图纸；四算量既有算法与回归 pass 判定未触碰。


## 0.28.14 — 2026-10-18（安装/电气替代版回归 + 回归清单 fallback 开关）

- 新增同项目替换版电气系统图回归清单 `cad-file-reader-ts-elec-sys.json`（kind=electrical，`dwg_dxf_fallback=true`），正式电气候选复核 1/1 通过：systems=1165、route_segments=1252、equipment=2430、circuits=1943、specs=1620，contract_valid=true，review_items=68。
- `run_real_dwg_regression.py` 支持清单级/用例级 `dwg_dxf_fallback`，扫描时自动追加 `cad_scan --dwg-dxf-fallback`（含缓存复扫分支），便于把需要 LibreDWG 回退的原图直接纳入常规回归。
- 自检：`cad_validate.sh` 校验 batch 报告通过；本轮不触碰图纸字节，产出仅存本机。


## 0.28.13 — 2026-10-18（LibreDWG fallback 集成 + 自检修复）

- 集成 LibreDWG `dwg2dxf` 回退：`read_cad.convert_dwg_to_dxf` 与 `cad_scan.py --dwg-dxf-fallback` 增加对常见安装目录（dwg2dxf 所在目录、brew、/usr/local）的自动发现；DWG 直读失败（含 `section map page not found`/`system section header out of range`/负 handle 等解析器上限）时自动转 DXF 复扫，几何/块几何回退到转换后的 DXF 计算。
- A3-3 电气原图 2 张（AC1027）经 LibreDWG 转 DXF 复扫成功：平面图文字 10812/图层 141/线段 10081；系统图文字 9982/图层 155/线段 9389；块引用合计 17931；领域候选需人工核对。
- 园林图块 rar 旧版 DWG 抽样转换：LibreDWG 可转 DXF（平面分析/古代园林建筑亭子/常用素材01 均 rc=0），已打通旧版块库回退路径。
- 自检修复：`cad_landscape_calibrate` 测试不再写技能包 institutes/，改用 `--override-path` 写临时目录；发布预检全量自测 167/167 通过、脱敏扫描 0 命中。
- 清理 CHANGELOG 中的项目名/绝对路径，发布合规 `check_release.py` 通过；manifest/SKILL version 同步为 0.28.13。

## 0.28.12 — 2026-10-18（第三批补齐：图审 22/22、PDF 扩容 15/15）

- 精装图审 zip 剩余 22 个 DWG 全量补齐：r1–r5 五批 22/22 通过；做法/立面/节点/平面系统/图纸均产出 components 候选，references 非每张必有，样本充分后以 components 作为图审批主可见口径。
- 系统图 PDF 扩容 15 例（给排水 5、电气/弱电 5、暖通 5）15/15 通过 `cad_pdf_ocr.sh --classify-only`。
- 跨区苗木表 II–IX 区 8/8 全量通过（plant_legends 281+/张），补齐第三批清单。
## 0.28.11 — 2026-10-18（第三批真图：图审/钢构/苗木/系统图 PDF）

- 精装图审 5 张真图回归 5/5 通过（做法表、立面、节点、平面系统图、B展厅平立面）；components/references 均有候选，geometry=0 属图审/立面/节点类预期，改用 components+references 作为该批校验主键并记入复核。
- 钢构深化图回归 3 张：桁架板、D 区 B1-16 交 A-K 深化图 2/2 通过（members 165/1522）；另一张审核图 9.5 仍为解析器上限（negative handle/offset 120040，DXF 转换同样失败），已列为 LibreDWG/ODA 缺口。
- 跨区苗木表 DWG 5/5 通过（plant_legends 281–384/张）；系统图 PDF 5/5 `cad_pdf_ocr.sh --classify-only` 通过。
- 园林景观CAD图块.rar 用 bsdtar 解出 1130 个 DWG，抽样 7 个 2015 老版 DWG 均报 `unsupported DWG version`，ezdwg 无法解析，记录为解析器上限（待 LibreDWG/ODA 或新版 unrar 后再补块库回归）。
- 自检：新增批报告的 `cad_validate.sh` 校验通过；发布合规红线未触及。
## 0.28.10 — 2026-10-18（第二期批量真图回归 + PDF 分类分支）

- 回归脚本 `scripts/run_real_dwg_regression.py` 新增 `kind="pdf"` 分支：PDF 走 `cad_pdf_ocr.sh --classify-only`，装饰/节点类 PDF 可纳入回归池。
- 真图池扩展至第二期补充替代 4 例（A3-3结构→A3-3附商业结构施工图、A4结构→A4-4附商业结构施工图、A3-3电气区→A3-1/A3-2 电气）全部 4/4 通过。
- 装饰侧另以本机 PDF（钢结构/防水节点）走 OCR 分类回归 10 例，10/10 通过。
- 自检：全量单测 167/167 通过；`cad_landscape_calibrate` 测试已改为临时目录覆盖写入，不再依赖技能包可写；`cad_validate.sh` 通过；`cad_release_scrub.py` 0 命中。
- 遗留：原 `经十一路A3-3#电气平面图12.11.dwg` / `电气系统图12.11.dwg` 为 ezdwg 无法解（section map page not found），暂以 A3-1/A3-2 同区电气图替代回归；属解析器上限，非识图/算量逻辑问题。

## 0.28.9 — 2026-10-16（园林植物词库扩充 + 市政/海绵识图规则修复）

- `packs/landscape-geometry/rules/plants.json` 并入本地植物名参考库（常用植物、西北温带荒漠区、园林景观CAD图块素材、分区苗木选型）。
- 仅扩充 `plant_trees` / `plant_shrubs` / `plant_groundcover` / `plant_other` 四组词表；不改块引用计数、不算数量、不改语义。
- 合并口径：已有词不移动不覆盖；新词按 乔木>灌木>地被>其他 归类；去除来源文件名残留的纯数字后缀。
- 验证：JSON 可加载；cad-file-reader 全量测试 167/167 通过；`白桦`/`蛇莓`/`辽东冷杉` 三个新词可分别按乔木/地被/乔木识别。

- 市政/海绵识图规则修复（`packs/municipal-geometry/rules.json`）：修复 `kerb`（路缘石）被 `road_centerline` 抢匹配的优先级 bug（kerb 前移）；
  新增系统别名 `heating`/`fire_protection`/`power`/`reclaimed_water`/`sponge_city`；新增构件 `road_grade`/`water_equipment`/`sponge_facility`/`permeable_pavement`，`inlet` 扩 `EQUIP_雨水斗`；
  新增图层别名 `DIM_*`/`管线-*`/`EQUIP_*`/`HEATER`/`道路中心标高`/`d11-总平面-道路`/`给排水设备`/`海绵*`；新增单测 `test_outdoor_layer_aliases_and_sponge_are_classified`。
- 真图回归扩到 8 例全通过（新增范村景观种植、范村室外综合管网、范村室外强电、酒店人防结构、范村海绵（总图/模块/设施）），全部 `contract_valid=true`。

## 0.28.8 — 2026-10-13（DWG 块名净化 + 园林识图发布，GitHub/SkillHub）

审查结论：Ponytail 确认本轮改动是最小可发布集合（自动转 DXF 复扫复用内置 ezdwg，无新增依赖）；skill-architect audit 无 ≥50 行大块章节需外移，包结构维持现状。
- `cad_scan` 增加 DWG 块名净化：
  - 新增 `_is_garble_name` / `_safe_block_key`，乱码块定义名替换为稳定占位 `_BLK#N`，`meta.block_defs` 与 DWG 块几何输出统一使用净化键，避免乱码污染 JSON/语义；
  - 块引用（INSERT）名解码为空/部分为空时自动加 note 提示“建议转 DXF 复核”，不再静默丢块级信息；
  - `--with-block-geom` 的块几何组装同样净化乱码块名，并附“疑似乱码”note。
  - 新增自动复扫：`--dwg-dxf-fallback`（或 `CAD_DWG_DXF_FALLBACK=1`）在检测到 DWG 块名解码为空/乱码时，用内置 ezdwg 转 DXF 后自动复扫一层再出结果；`read_cad.convert_dwg_to_dxf` 修复临时目录 DXF 被提前删除的问题（复制到独立临时目录再返回）。
- 验证（运行时 python，全量 163 项通过）：真图 01绿化设计说明_t3.dwg 直扫块引用名空（233 条）；开启 `--dwg-dxf-fallback` 后自动转 DXF（23065/23066 实体）复扫出块引用 `_CLOSEDFILLED`×272、文字 1116 条，块级信息不再丢失；全部 `final_quantity=false`。

## 0.28.7 — 2026-10-13（本地优化：园林识图大图闸门 + DWG 块内几何短预算试探，未发布）
- `cad_scan --with-block-geom` 增加 DWG 分支：短预算探块名 + 实体归属（decode_entity_placements）+ LINE/LWPOLYLINE，按块定义聚合内部几何，输出结构与 DXF 路径一致；超时/缺数据仅加 note，自动回退近邻几何，不阻塞整图。
- 新增 `placements` 子进程解码通道，C 层解码仍走子进程+预算回收内存。
- 大尺寸图纸闸门：
  - 新增 `--geom-budget`（几何/块几何独立时间预算）与 `--geom-max-rows`（几何线段数上限，超限截断并 note，自动回退近邻几何）；
  - `--roi` 在无缓存直跑时提前过滤文字/插入/几何线段，减少大图下游处理量；开缓存时仍先存全量、查询时裁剪，避免缓存被局部数据污染；
  - 缓存档案加入 `geom_budget`/`geom_max_rows`，防止不同几何闸门混用同一缓存。
- 单测新增 9 项（DWG 块几何 5 项 + 大图闸门 4 项），全量 157 项通过（运行时 python）；`final_quantity` 均 false。
- 词库结构瘦身：`packs/landscape-geometry/rules.json`（8.8KB→3.9KB）拆出 `rules/plants.json`、`rules/hardscape.json` 主题文件；`cad_common.load_rules` 后合并主题文件，旧单文件规则与 CLI 全兼容。
- 校准建议清洗：`suggest_text_word` 在排除词命中时直接拒绝（花砖/花园/槐荫/分理处/宿舍/公司等），真实大图自动候选从 17 个降到 3 个真实植物词；`plant_exclude_phrases` 扩到 38 项。
- 经十一路设计院词库已生成 `packs/landscape-geometry/institutes/jingyilu.json`：紫叶矮樱/柿树/山楂树→乔木，`--verify` 与带院复验通过（3 词均正确分类）；人工复核补充棣棠/金银木/黄栌→灌木、淡竹→其他，带院复验 4 词分类正确；全量 160 项通过（运行时 python）。
- `--roi` 无缓存直跑补测（26MB 种植总图，ROI=496000,4056000,498500,4058000）：TEXT 14332→9602 条、带坐标记录 0 条在 ROI 外、几何输出 segs=13670、峰值 177MB/11.7s，证明大图局部识图正确裁剪（解码全图峰值仍在，下游处理量明显下降）。
- 真实图纸校准驱动新增非植物排除词 `plant_exclude_phrases`（23 项：花砖/地址/银行/分理处/宿舍/树形饱满/主景树/兰亭/鉴筑等）：`plant_classify` 命中即不分类，真实大图 693 条 plant_legends 中花砖、银行分理处、宿舍、树形、主景树等误判全部清零；真实植物（国槐/紫薇）仍正常分类；真图复验 bad_hits=0。
- 真实图纸实测（外盘经十一路安置区景观施工图）：
  - 01绿化设计说明_t3.dwg（2.2MB）：短预算块几何试探 4.1s/峰值 56MB，命名块命中，`--geom-max-rows 30000` 截断 note 生效；
  - 02种植总图+苗木表_t3.dwg（26MB）：大图闸门 11.7s/峰值 181MB，块几何试探 3 命名块命中 1，几何 20000 上限截断并回退近邻几何，园林输出 plant_legends=693、plant_block_fingerprints=1。

## 0.28.6 — 2026-10-13（本地优化：园林 PDF/苗木图例清洗，未发布）
- 园林景观识图（`packs/landscape-geometry`）：
  - 苗木/植物图例文字自动拆成 植物名 + 规格（`plant`/`spec`/`legend_raw`），JSON/MD/CSV 同步带出，方便按种名复核；
  - 英文/ASCII 图例词兜底（`plant_english_aliases`：tree/shrub/groundcover/lawn/grass 等按乔/灌/地被候选）；
  - `hardscape_text_tokens` 扩充铺装材料类（透水砖/花岗岩/青石板/木平台/防腐木/艺术地坪等，49 项）；
  - PDF 入口 `cad_landscape_pdf --pages 1,3-5` 支持只处理部分页，OCR 与矢量几何提取同时生效；
  - PDF 矢量几何 `pdf_geometry_candidates` 固定 `review`、`pdf_no_layer_geometry`，不参与闭合域/算量；
  - 新增词库覆盖审计 `audit.unclassified_legend_words`：列出带种植/图例上下文但未分类的候选词频，快速定位具体设计院缺词，并过滤表头/图纸类型尾词；
  - 设计院校准新增 `--verify`：写覆盖后自动复验 before/after 分类变化；
  - 文字图例校准闭环：`text_word_suggestions` 从覆盖审计自动提词初判，`--write-text-words` 把 conf≥0.8 植物词并入该院词表；
  - 扫描版 PDF OCR 全链路回归验证（raster PDF → OCR → landscape 坐标/候选），OCR 错字标 review；
  - `cad_landscape_pdf` 支持多文件/目录批量：按 `<茎>.landscape.*` 分开输出 + `_batch_summary.json`。
- 真 PDF 全链路回归通过：矢量(中文嵌入字体) → CAD_PDF_OCR → landscape，苗木图例清洗+规格+PDF几何证据输出正确。
- 全量自测 143 项通过（运行时 python）；全部输出 `final_quantity=false`。

## 0.28.5 — 2026-10-12（真图回归纳入发布预检）
- `run_preflight.sh` 强制纳入真图回归（`--manifest <真图清单>` 时执行 8 张真图回归，缺清单明确跳过并提示），全量自测 + 发布合规扫描统一为发布预检。
- 三平台版本基准对齐：SKillHub 运营更新不回写本机，仅以本机功能更新发布。

## 0.28.1 — 2026-10-12（完整性校验强化，三平台重新发布）

- `install_vendor.sh` 改用同 Release 的 `SHA256SUMS` 对完整包做 SHA-256 校验；校验文件缺失或哈希不一致一律拒绝解压/执行。
- 移除无校验文件的旧版本回退下载路径，只允许当前版本（含校验文件）下载；离线/缺校验文件时给出明确报错和 pip 兜底提示；默认版本更新为 0.28.1。
- 三个算量技能的 `ensure_base.sh` 同步增加底座完整包 SHA-256 校验与包内 manifest 版本校验，杜绝“下载即信任”。

## 0.27.0 — 2026-10-11（文档与安装优化，发布 SkillHub/GitHub/clawhub）

按 SkillHub 评测优化：文档瘦身 + 安装一条命令 + 依赖自检 + 30 秒样例演示。

- README 由 16KB 精简到 3KB：移除历史小版本堆叠概览，只保留最新能力一句话、一条命令安装、快速开始与边界链接。
- CAPABILITIES 改为能力/边界矩阵（约15KB → 约4KB），删除与 SKILL/pack-index 重复的命令示例；业务边界统一引用 pack-index。
- 新增 `scripts/setup.sh`：Python 3.10 检查 → vendor 补齐 → `.env`（PYTHONPATH）→ 依赖自检，一条命令完成轻量包安装。
- 新增 `scripts/deps_check.sh --minimal`：输出 numpy/ezdwg/ezdxf/fontTools 可用性与降级提示。
- `scripts/install_vendor.sh` 增加幂等分支：vendor 已存在直接“已存在，未变更”，无需重复下载；支持 `CAD_FORCE_INSTALL=1` 强制重装；安装后提示 NOTICE 许可证。
- 新增 `scripts/demo.sh` + `examples/sample_room.dxf`：一条命令跑完整识图→测量→契约校验，展示首屏 JSON（证据/置信度/复核）。
- `manifest.json`：description 标注安装一条命令；scripts 清单补充 setup/deps_check/demo。
- `run_preflight.sh` 新增 outputs 跳过（历史发布校验文件不入扫描）。
- 验证：全量自测 128/128 通过；样例 DXF 识图/测量/契约校验通过；脱敏扫描 0 命中。

## 0.26.4 — 2026-10-09（本地优化，未发布）

输出深度用户可选 + Word/Excel 导出。

- 精简模式改为显式选项：默认完整输出；`--concise` 精简候选主干（省 Token），`--full`/`--with-evidence` 恢复完整；`CAD_CONCISE=1` 可全局设为精简默认。
- `run_cad.sh` 支持 `--concise` 并在转发前剥离开关；`cad_scan.py` 同步支持 `--concise/--full/--with-evidence`。
- 新增 `scripts/cad_export.py`：把雷达扫描结构化结果导出为 Excel(.xlsx) / Word(.docx)，多 Sheet/分节（构件候选、规格表、钢筋汇总、建筑做法）；`cad_scan --format xlsx|docx` 可用（需 `--out`）。
- SKILL.md 增加精简输出与 xlsx/docx 用法示例。

## 0.26.3 — 2026-10-09（本地优化，未发布）

精简输出契约，降低下游 Token 开销。

- 默认精简契约：`CAD_CONCISE=1` 时 `contract.candidates`/`review_candidates` 只保留候选主干字段，`evidence` 置空、不展开长数组；`--full`/`--with-evidence` 可恢复完整证据。
- `scripts/run_cad.sh` 默认设置精简模式，并支持 `--full`/`--with-evidence` 开关。
- `cad_contract.py` 支持 `concise=` 参数；校验对精简候选向后兼容。
- SKILL.md 补充精简输出用法说明。

## 0.26.2 — 2026-10-09（本地优化，未发布）

继续补充专业识图规则包并强化契约。

- 新增 `packs/doors-windows-stairs-insulation-waterproof/`：门窗/楼梯/保温/防水识图候选（门窗编号、楼梯梯段/休息平台/栏杆扶手、保温层/防水层、标高/编号证据），输出统一候选契约。
- 新增 `packs/fire-prevention-accessibility-green-energy/`：防火/无障碍/绿建节能识图候选（防火分区、疏散路线、防火门/卷帘、无障碍坡道/通道/卫生间、屋顶绿化/雨水花园/光伏/节能做法，编号/标高证据）。
- 新增入口 `scripts/cad_doors_windows_stairs_insulation_waterproof.sh`、`scripts/cad_fire_prevention_accessibility_green_energy.sh`（及 .py 配套入口）。
- `rules/legends.json` 扩充 2 组图例词库：门窗楼梯保温防水、防火无障碍绿建节能。
- 契约增强：候选输出 `confidence_score`（0–1 主置信度，与 confidence 同值），schema/校验同步支持。

## 0.26.1 — 2026-10-09（本地优化，未发布）

按专业方向建议新增两个规则包并扩展图例词库。

- 新增 `packs/bridge-tunnel-road-traffic/`：桥梁/隧道/道路线形/交通设施识图候选（桥墩、桥台、盖梁、支座、隧道洞口、衬砌、路线中线/平竖曲线、交通标志标线、护栏、信号灯），输出图纸类型/系统/构件/桩号坐标/图层证据。
- 新增 `packs/pile-foundation-slope/`：桩基/基坑/边坡/地基处理识图候选（桩型、承台、支护桩、地下连续墙、内支撑、锚索、锚杆、挡墙、抗滑桩、护坡、搅拌桩/CFG/强夯、监测点），输出图纸类型/系统/构件/桩号标高/图层证据。
- 新增入口 `scripts/cad_bridge_tunnel_road_traffic.sh`、`scripts/cad_pile_foundation_slope.sh`，注册到统一候选契约（final_quantity=false）。
- `rules/legends.json` 扩充 2 组图例词库：桥梁隧道道路交通 15 词、桩基基坑边坡 24 词。
- 验证：两个新规则包自测 2 项通过。

## 0.26.0 — 2026-10-08

新增 PDF 图纸识图能力与发布合规修复（按本机 skill-publisher / skill-architect 审计落地）。

- 新增本机 PDF 识图入口 `scripts/cad_pdf_ocr.sh` / `.py`：先用 pdf-inspector 做类型分流（`text/scanned/mixed` → `pdf_vector/pdf_raster/pdf_hybrid`），矢量页取原生文字与变换矩阵，扫描/混合页用 `pdftoppm` 渲染后调本机 image-ocr 出线性文字候选。
- 输出 `page_index` / `page_bbox`（PDF 点）、`source_bbox_px`、扫描/混合页缺图层口径（`missing_layer/missing_unit/missing_scale`），全部候选固定 `final_quantity=false`、进 `review_candidates`。
- 图签栏元数据锚点：版式优先（右下角区域）+ 关键词回退，`pdf_meta.title_block` 只做跨格式元数据锚点，需人工核对。
- 矢量 PDF 原生文字坐标复核入口 `scripts/cad_pdf_vec.sh` / `.py`：`x/y/width/height/font/font_size/page`，单位 PDF 点，不参与测量。
- 两级缓存（文件级 PDF 元数据 + 页面级 OCR 行结果）与页面级 `--workers` 并行（默认≤3），`--classify-only`、`--force`、`--cache-dir`。
- 契约增强：`source_format` 字段标识 `pdf_vector/pdf_raster/pdf_hybrid`；`cad_contract.py` 注册 `pdf_meta` 章节；`cad_validate` 校验 PDF 契约样例。
- 发布合规修复：移除脚本内硬编码本机绝对路径（本机绝对路径），改为环境变量 + `Path.home()` 运行时回退；文档脚本引用改为显式完整文件名，避免发布检查误报 missing_script。
- 验证：全量自测 124 项通过；发布前脱敏扫描 70 文件命中 0 处；本机真实 DWG 回归 3/3 pass（结构/总图/电气）；缓存验证 3/3 `cache_hits=1`。

## 0.25.0 — 2026-10-05

按优化建议落地 P0/P1 识图准确率与契约增强（纯规则/轻量知识表，不引入视觉模型）。

- 旋转感知标注：`cad_scan` DXF 流式解码与 `read_cad` 捕获文字实体旋转角（`rotation`）；`cad_scan.analyse()` 按 0-180° 每 5° 分桶加入位置键，同位置不同旋转拆分为独立标注位置，`cad_interpret._scope_key` 同步带上旋转桶，供斜向标注正确归属与证据追溯。
- 图例知识表：新增 `scripts/cad_legend.py`、`scripts/cad_legend.sh` 与 `rules/legends.json`，按专业扩充到 14 组 205 个关键词（消防报警、照明、动力、弱电智能、给排水、暖通、消防水、钢结构、市政、人防、预制、装饰、幕墙、测量标注），支持 `symbols` 符号指纹表（12 组块/符号别名）优先匹配块引用；同名 INSERT 文字不再覆盖块指纹。输出 `legend_matches` 候选和 `discipline_refs`。
- 契约增强：candidate 新增可选 `rotation`、`confidence_scores`（证据子项强度）、`discipline_refs`（跨专业视角），schema 与 `cad_validate` 向后兼容。
- `cad_contract.py` 注册 `legend_matches` 章节；`test_cad_legend.py` 3 项（含符号指纹去重优先级），完整自测 95 项通过。
- 端到端示例验证：图例词库命中 6 条候选，`cad_validate.sh` 校验通过。
- 边界不变：全部候选固定 `final_quantity=false`，不输出工程量/材料量/造价；图例词库只做识图辅助不改算量口径。

## 0.24.0 — 2026-10-05

新增纵深专业识图引擎与 5 个深化识图包（按建议继续补充）。

- 新增通用引擎 `scripts/cad_deep_geometry.py`：读取 `cad_scan` 详情 JSON，按 `--pack` 加载对应规则包，输出 `*.<pack>.json/md/csv` 与 `cad-file-reader/v0` contract，统一固定 `final_quantity=false`。
- 新增 `packs/hvac-plumbing-geometry/` + `scripts/cad_hvac_plumbing_geometry.sh`：给水/排水/消防水/暖通/防排烟/泵房/支吊架图纸类型与系统，管道、风管、风机盘管/风口/设备、支吊架构件，管径（DN/De/D）、标高、设备/立管编号候选。
- 新增 `packs/interior-finish-geometry/` + `scripts/cad_interior_finish_geometry.sh`：精装修平面/立面/节点/做法表/门窗表/固定家具，地面/墙面/顶棚/踢脚/家具/防水构件，做法编号/材料/标高/节点候选。
- 新增 `packs/curtain-wall-geometry/` + `scripts/cad_curtain_wall_geometry.sh`：玻璃/石材/金属/单元式幕墙，立柱/横梁/面板/开启/预埋件/胶条构件，分格/标高/板块/预埋编号候选。
- 新增 `packs/civil-defense-geometry/` + `scripts/cad_civil_defense_geometry.sh`：防护单元/人防墙/防护密闭门/防爆波活门/滤毒通风/洗消/人防电气，门号/抗力等级/标高/设备编号候选。
- 新增 `packs/precast-geometry/` + `scripts/cad_precast_geometry.sh`：预制墙/叠合板/预制楼梯/预制梁柱/预埋件/连接节点，构件编号/桁架筋/标高/预埋编号候选。
- `cad_contract.py` 注册 `hvac_plumbing_geometry`、`interior_finish_geometry`、`curtain_wall_geometry`、`civil_defense_geometry`、`precast_geometry`（line）章节。
- 新增 5 组（10 项）合成回归；完整自测 87 项通过。
- 边界不变：只出识图与证据候选，不展开管道长度/风管面积、不输出饰面面积/排版数量/幕墙面积/板块数量/人防或预制构件数量/体积、材料量或造价。
- 真实回归：本机知识库 7 张真图验证（结构/总图场地/给排水喷淋/人防/精装修/幕墙/预制装配）7/7 pass；幕墙用会展2#立面/LM，预制装配用安置五装配式改铝膜结构，回归清单仅存本机、发布前脱敏。
- 发布前脱敏自检通过（扫描 63 文件，命中 0 处）。

## 0.23.0 — 2026-10-05

新增结构识图候选包与总图/场地识图候选包（按用户建议补充的两个专业识图能力）。

- 新增 `packs/structural-geometry/`（SKILL.md + rules.json）与 `scripts/cad_structural_geometry.sh`、`scripts/cad_structural_geometry.py`：识别结构平面/配筋/基础/楼梯/节点详图/柱表/结构说明等图纸类型，混凝土/钢筋/基础/楼梯/预制/加固系统，梁/板/柱/墙/基础/楼梯/洞口加强/节点加强构件，HPB300/HRB400 配筋标注（直径@间距、纵筋/箍筋/附加筋/负筋/拉筋/分布筋），KL/WKL/KZ/YBZ/GBZ/LB/WB/Q/CT/FB/JZL 结构编号，节点/轴网/标高候选；输出 `*_structural.json/md/csv` 与 contract。
- 新增 `packs/site-geometry/`（SKILL.md + rules.json）与 `scripts/cad_site_geometry.sh`、`scripts/cad_site_geometry.py`：识别总平面、竖向、管线综合、道路纵横断面、挡土墙/边坡、停车、景观图纸与系统，红线/道路/人行道/路缘石/停车位/挡墙/护坡/排水沟/雨水口/检查井/管线/高程点/土方挖填/绿化铺装构件，桩号/坐标/标高/盘区编号标注候选；输出 `*_site.json/md/csv` 与 contract。
- `cad_contract.py` 注册 `rebars`（text）、`structural_geometry`（line）、`site_geometry`（line）章节；统一候选契约保持 `final_quantity=false`。
- 缺几何、缺图纸类型、缺比例/单位、缺图层、配筋/标高/桩号未绑定几何进入 `review`；不默认按比例推算。
- 新增结构识图测试 2 项（结构提取通过、缺比例/几何进入复核）与场地识图测试 2 项；完整自测 77 项通过。
- 真实回归：`run_real_dwg_regression.sh` 支持 `kind=electrical|structural|site`；本机知识库结构 DWG（会展梁板）与总平面 DWG（济南国贸总平面图）均通过（2/2 pass）。
- 边界不变：本技能只做识图和证据候选，不输出混凝土方量、钢筋吨位、土方量、道路面积、管线长度汇总、材料量或造价。

## 0.22.0 — 2026-10-05

电气识图继续增强：新增消防、弱点/弱电与智能化识图能力（建筑电气之后第二步）。

- 新增 `domain_rules`：`fire_protection`（消防）、`weak_current`（弱点/弱电）、`intelligent_building`（智能化）三领域系统映射；`domain_of` / `domain_candidates` 把系统、设备、回路、路由、标注候选按领域分组，JSON/Summary/Markdown/CSV 输出 `fire_protection`、`weak_current`、`intelligent_building` 字段和 `domain`/`domain_label`。
- 图纸类型扩充：消防水/喷淋平面、消防联动平面、防排烟平面、气体灭火平面、智能化平面、综合布线平面（PDS）、CCTV 平面、广播/会议（PA/AV）平面。
- 专业系统扩充：消防水、喷淋、气体灭火、防排烟、疏散、消防联动、消防泵、综合布线、门禁、广播/会议、BAS、能耗计量、智能照明、IBMS、停车等。
- 路由规则新增消防火警环路（`fire_loop`，system=fire_alarm）和弱电信号总线（`signal_bus`，system=weak_current）。
- 设备规则新增防火卷帘/防火门、消防泵、消防控制主机、排烟口/阀/风机、网络设备、摄像机、门禁设备、广播音箱、DDC/BAS 传感器、能耗计量表、智能照明面板等。
- 回路前缀扩充 FAS/FA/FBF/FB/FBN/XFB/XS/XQ/CCTV/PDS/ACS/PA/AV/IBMS/BMS；规格识别扩充 UTP/STP/CAT5E/CAT6/GYXTW/GYTA/FIBER 等弱电/光缆线型。
- `cad_contract.py` 注册 `fire_protection`、`weak_current`、`intelligent_building` 章节（device），统一候选契约保持 `final_quantity=false`。
- 新增 `test_fire_weak_current_intelligent_domains` 回归；电气识图测试 4 项通过。
- 新增本机真实 DWG 回归入口 `scripts/run_real_dwg_regression.sh` / `.py`：读取 `--manifest` 真图清单，串接 `cad_scan` + `cad_electrical_geometry`，按领域候选数核对并输出脱敏报告；真图清单在技能包之外，发布内容不含真实图纸路径。
- 真实回归验证：酒店消防报警、会展弱电、I-1号楼智能化三张本机知识库 DWG 均通过，消防/弱点/智能化领域候选均>0（3/3 pass）。
- 下一步按发布流程执行 skill-publisher，发布前运行脱敏守卫。

## 0.21.0 — 2026-10-05

新增电气专业识图中间数据模块（第一步：建筑电气）。

- 新增 `scripts/cad_electrical_geometry.sh` 与 `packs/electrical-geometry/`（SKILL.md + rules.json）：识别变配电、照明、动力、应急照明、火灾报警、安防、弱电智能化、防雷接地图纸类型与系统。
- 输出桥架/母线/导管/电缆/导线路由候选、配电箱/柜、灯具、开关插座、探测器、报警设备、防雷接地设备候选，以及回路编号（WL/WP/WE/EM/L/M）与回路规格标注候选。
- 回路只做候选与复核，不展开芯数/线长；不输出电气材料量、负荷、照度、母排、造价或结算量。
- `cad_contract.py` 注册 `circuits/specs/lightning` 章节，统一候选契约保持 `final_quantity=false`。
- 新增 `test_cad_electrical_geometry.py`（3 项）；完整自测通过。
- 仍未接入：真实电气 DWG 回归图；消防/智能化按约定排在电气之后，不在本版本。

## 0.20.1 — 2026-10-05

修复 SkillHub 轻量包自动下载与概况增强。

- `scripts/install_vendor.sh` 兼容 `cad-file-reader-full-<ver>.zip` 与 `cad-file-reader-<ver>-full.zip` 两种 GitHub Release 命名，安装后可自动下载对应版本 vendor。
- Manifest / SKILL/README 概况补充 P0–P5 优化简介：统一候选契约/置信度分层、大图缓存与局部解析、图层/块语义、MEP 拓扑增强、图纸对比。
- 完整自测 69 项通过。

## 0.20.0 — 2026-10-05

发布前重构整理（无功能/契约变更）。

- 新增 `scripts/cad_common.py`，抽取 `compact`、`load_rules`、`pattern_hit`、`match_rule`、`segment_length`、`peak_rss_mb`、`file_name` 等跨脚本公共函数。
- `cad_semantics.sh`、`cad_compare.sh` 改用统一入口 `scripts/run_cad.sh`，移除硬编码 Python 路径。
- 完整自测 69 项通过。

# 更新记录



## 0.19.0 — 2026-10-04

识图候选可信度、语义/拓扑/对比与交接稳定性增强。

- 新增 `cad-file-reader/v0` 统一候选契约：`confirmed_evidence`、`inferred_candidate` 和 `review_required` 三层置信度；标准复核原因词表、中文 `review_notes`、确定性候选 ID 和交接校验。
- 新增大图证据缓存、`--roi` / `--sheet` 局部解析、缓存读写观测和 `cad_cache_admin` 安全治理。
- 新增 `cad_semantics.py` / `cad_semantics.sh`：图层语义、块语义和块实例关联候选；支持上限与关联半径控制。
- `cad_mep_geometry` 新增 `mep_relations`：设备—管段、立管—管段、端点连接和系统冲突关联；缺图层/系统、冲突或距离异常进入复核。
- 新增 `cad_compare.py` / `cad_compare.sh`：对比图层、块、文字和几何的增删与移动；同图对比输出 0 变化。
- 新增图层/块语义与图纸对比回归测试；完整测试 69 项通过。
- 本地解析边界不变：所有候选固定 `final_quantity=false`，不输出最终工程量、材料量、造价或结算量。

## 0.18.0 — 2026-09-20

测量候选层与识图/算量边界强化。

- 新增 `cad_measure.py` / `cad_measure.sh` 和 `packs/measurement-candidates/`。
- 从 `cad_scan` 详情、装饰、安装、钢结构、市政识图 JSON 生成长度、面积、体积候选。
- 输出契约：`cad-measurement-candidates/v1`；每条候选包含图面值、换算值、比例/单位/空间依据、计算式、置信度、复核原因、源 ID 和证据坐标。
- 闭合多边形使用鞋带公式；显式文字测量值可直接采用；外接框面积只作定位证据；体积只在显式体积或面积×显式厚度/高度时生成待复核候选。
- `model` 空间只按坐标单位换算；只有 `paper/layout` 空间且比例明确时才应用 `1:N`；缺比例/单位时 `value=null` 并转 `review`。
- 所有测量固定 `final_quantity=false`；不重新引入扣减、重叠、做法映射、损耗、分账、清单量、材料量、造价或结算量。
- 新增 7 项合成回归，覆盖显式测量、多边形面积、缺单位复核、外接框复核、体积复核、MEP 路由证据和 paper-space 比例。

## 0.17.0 — 2026-09-20

识图与算量职责拆分。

- `cad-file-reader` 收口为识图、几何候选、证据提取和复核边界；不再输出最终工程量、体积、面积、材料量、造价或结算量。
- 原梁、板、柱、墙、楼梯、洞口、预制底板、混凝土等级分账和结构算量流水线迁移到 `tujian-suanliang`（本机目录 `shangwu-suanliang`）。
- 删除 `cad_quantity_pipeline.sh`、`--axis-grid`、`--axis-label`、`--thk-mm`、`--col-height-mm`、`--floor-beam-json`、`--floor-label`、混凝土 CSV/Markdown 和楼层梁混凝土初算输出。
- 保留 `cad_scan`/`cad_interpret` 的文字、图层、图框、几何线段、构件标注、净跨/支座候选和原文证据，供专项算量 skill 调用。
- 更新 manifest、pack-index、README、CAPABILITIES 和 agent 入口，移除算量路由。

# Changelog

## 0.16.0 — 2026-09-20

市政专业识图中间数据层。

- 新增 `cad_municipal_geometry.py` / `cad_municipal_geometry.sh` 和 `packs/municipal-geometry/`。
- 识别道路、排水、管网、桥梁、涵洞、隧道、挡墙、交通和道路照明等市政图纸类型和专业系统。
- 支持道路中线、路缘石、人行道、路面结构层、路基、边沟、检查井、雨水口、管道、桥墩、桥台、桩基、承台、箱梁、涵洞和隧道衬砌等构件候选。
- 提取桩号、标高、`X/Y` 坐标、管径、坡度、尺寸、材料、做法和规范引用证据。
- 输出契约：`cad-municipal-geometry/v1`；保留图层、几何、文件、图框、坐标和原文证据。
- 缺比例/单位、缺几何、图层未分类、系统/构件无法映射、材料或标高缺失时进入 `review`。
- 只做识图和证据，不输出面积、长度汇总、数量、材料量、造价或结算量。

## 0.15.0 — 2026-09-20

钢结构识图中间数据层。

- 新增 `cad_steel_geometry.py` / `cad_steel_geometry.sh` 和 `packs/steel-geometry/`。
- 识别钢结构图纸类型、结构系统、构件、截面、连接、材料、涂装、节点、轴网/标高和钢构件几何候选。
- 支持钢柱、钢梁、桁架、支撑、檩条、拉条、墙梁、平台、钢楼梯、栏杆、预埋件、节点板和加劲肋。
- 支持 H 型钢、槽钢、角钢、圆管、方矩管、C/Z 型檩条和钢板截面，以及常用钢材牌号和涂装做法。
- 输出契约：`cad-steel-geometry/v1`；保留图层、几何、文件、图框、坐标和原文证据。
- 缺比例/单位、缺几何、图层未分类、构件编号无法映射或截面/材料缺失时进入 `review`。
- 只做识图和证据，不输出钢材重量、面积、长度汇总、材料量、造价或结算量。

## 0.14.0 — 2026-09-20

安装识图增强：系统拓扑与竖向路由候选。

- 新增 `topology`：按文件、图框和专业系统建立路由连通分量，输出闭合环、分支、开放端点、孤立段和复核原因。
- 新增 `vertical_routes`：把 `JL/PL/WL/...` 等立管编号和竖向文字关联到最近路由段，保留图面距离、方向、图层、文件、图框和证据。
- 新增竖向几何图层规则 `RISER/立管/竖向/竖管/管井/SHAFT`；只有几何命中而无编号证据时强制进入 `review`。
- 输出契约升级为 `cad-mep-geometry/v2`；新增 `--link-tolerance` 关联距离参数。
- 增加通用合成回归：闭合环拓扑、开放端点拓扑、立管关联和竖向几何复核。
- 只做识图、关联和拓扑候选；不输出安装工程量、材料量、损耗、造价或结算量。

## 0.13.0 — 2026-09-20

安装专业识图中间数据。

- 新增 `cad_mep_geometry.py` / `cad_mep_geometry.sh` 和 `packs/mep-geometry/`，从 `cad_scan` 详情 JSON 提取安装识图候选。
- 识别图纸类型：平面、系统、干线、详图、材料表/图例。
- 识别专业系统：电气、给排水、消防水、暖通、火灾报警、应急照明、弱电和燃气。
- 识别路由段：电线、导管、电缆、桥架、母线、给水管、排水管、消防管、喷淋管、风管、燃气管和通用 MEP。
- 识别设备/器具：配电箱、灯具、开关插座、风机、风口、风阀、水泵、阀门、喷头、探测器、报警设备、卫生器具和仪表。
- 提取回路规格、管径、风管尺寸、设备编号、系统标签、楼层标签和立管编号候选。
- 增加端点吸附、开放端点、汇聚/分支和孤立段连通性审计。
- 输出契约：`cad-mep-geometry/v1`；保留图层、几何、文件、图框、坐标和原文证据。
- 缺几何、缺比例/单位、MEP 图层未分类或立管归属不明进入 `review`。
- 只输出安装识图候选和证据；不输出安装工程量、材料量、损耗、造价或结算量。

## 0.12.0 — 2026-09-20

P2 外墙分格与保温分区候选。

- 新增 `exterior_wall_zones`：识别外墙、保温层、防火隔离带、女儿墙内侧和立面饰面候选。
- 提取材料、保温/隔离带厚度、显式标高和对应图层几何证据。
- 保温、防火隔离带和女儿墙内侧缺厚度、缺标高或标高冲突时进入 `review`。
- 标高单位缺失时按 `m` 暂记并强制进入复核，不自动确认。
- 输出契约升级为 `cad-descriptive-geometry/v7`，摘要和 Markdown/CSV 增加外墙分区字段。
- 增加通用合成图回归：外墙/保温/隔离带/女儿墙材料与厚度识别、缺几何强制复核。
- 只输出候选中间数据，不输出外墙面积、保温面积、材料量或最终工程量。

## 0.11.0 — 2026-09-20

P1 楼梯/坡道/台阶初稿。

- 新增 `stair_ramp_steps`：识别楼梯、坡道、台阶文字和对应图层几何候选。
- 提取显式展开面积/投影面积、级数、坡度、尺寸和分项材料文字证据。
- 保留匹配图层的几何外接框和线段证据；几何外接框不当作可确认面积。
- 缺显式面积、缺材料、缺匹配几何或文字缺坐标时进入 `review`。
- 输出契约升级为 `cad-descriptive-geometry/v6`，摘要和 Markdown/CSV 增加初稿字段。
- 增加通用合成图回归：三类构件识别、面积/材料保留、缺面积强制复核。
- 只输出待确认初稿，不自动确认展开面积、材料量或最终工程量。

## 0.10.0 — 2026-09-20

P1 顶棚分区候选。

- 新增 `ceiling_zones`：提取主吊顶、检修口、灯具带、造型分区和梁/降板影响候选。
- 按坐标绑定显式吊顶标高/高度证据；`mm` 归一为 `m` 后检查冲突。
- 检修口、灯具带和造型分区按外接框包含关系挂到主吊顶，保留父分区索引。
- 缺显式标高、标高冲突、坐标轴超限、主/附属混合候选或复杂非轴对齐造型进入 `review`。
- 输出契约升级为 `cad-descriptive-geometry/v5`，摘要和 Markdown/CSV 增加顶棚分区字段。
- 增加通用合成图回归：检修口父子分区、标高证据和缺标高强制复核。
- 只输出可复核中间数据，不输出吊顶面积、扣减面积、材料量或最终工程量。

## 0.9.0 — 2026-09-20

P1 墙面分段候选。

- 新增 `wall_segments`：把闭合轴对齐房间边界拆成 `clear` / `opening` 子段。
- 按坐标绑定显式墙高、墙面高度、层高或净高证据；`mm` 归一为 `m` 后检查冲突。
- opening 子段保留门窗编号、门窗图层和几何线段证据；不计算扣减面积或墙面面积。
- 缺墙高、墙高冲突、非轴对齐墙段、零长度墙段、无效边界或未绑定房间进入 `review`。
- 输出契约升级为 `cad-descriptive-geometry/v4`，摘要新增墙段总数与候选数。
- 增加通用合成图回归：洞口分段、显式墙高候选、无墙高强制复核。

## 0.8.0 — 2026-09-20

P0 通用识图中间数据增强。

- 新增闭合房间边界候选：输出多边形、外接框、绑定房间名和证据线段；坐标轴数量超限时显式截断并转入复核。
- 新增门窗洞口到墙线和房间的归属候选：输出墙图层、墙线段、图面距离、房间边界和待确认原因。
- 新增做法编号到节点详图索引候选：保留做法、节点、文件、图框和坐标证据。
- 房间边界、节点索引和门窗几何的异常项统一进入 `review`。
- 输出契约升级为 `cad-descriptive-geometry/v3`；文件索引统一还原为真实文件名。
- 降低闭合搜索坐标轴上限到 24，防止复杂图盲目扩大组合；截断项必须复核。
- 增加通用合成图回归：闭合房间、洞口贴墙、做法节点和缺几何复核。

## 0.7.0 — 2026-09-20

P0 装饰中间数据修正。

- `C15~C89` 等混凝土强度等级不再误判为窗编号，`C30/C35/C40` 增加回归覆盖。
- 房间词所在行未绑定做法编号时转入待复核，不生成空做法房间表。
- 门窗、比例、单位和几何索引还原 `cad_scan` 文件索引为真实文件名。
- 单位识别支持图面显式单位和带 `m/mm` 尺寸上下文；缺单位保持待复核。
- 真实项目详情 JSON 回归通过；具体项目数据只保留在本机，不进入发布包。

## 0.6.0 — 2026-09-20

新增画法几何 / 装饰中间数据层。

- 新增 `packs/descriptive-geometry/SKILL.md` 和识图规则 JSON。
- 新增 `cad_descriptive_geometry.sh`：从 `cad_scan --detail-json` 提炼视图、比例、单位、房间、门窗和做法候选。
- 输出 JSON / Markdown / CSV 证据台账，保留图层、坐标、图框和原文。
- 增加平面/立面/剖面/详图投影校验边界，候选不直接计入工程量。
- 增加合成详情 JSON 行为测试，覆盖视图、房间、门窗、做法和证据输出。

## 0.5.0 — 2026-09-18

规范/图集辅助与 Token 架构升级。

- 新增 `cad_normative`：从图纸说明中识别规范/图集引用，匹配 54 条元数据，其中 46 条可定位知识库相对入口。
- 支持斜杠/无斜杠变体、基础编号/年版编号匹配，自动提示现行、旧版、待确认和未索引状态。
- 输出缺少设计输入（混凝土等级、抗震等级、保护层等）与多图框参数冲突；只提示风险，不判定条文合规。
- 主入口文档从约 106 KB 精简到约 7.5 KB；算量流程说明从约 105 KB 精简到约 2 KB，长流程保留在专用包历史文件中按需读取。
- 规范索引仅保存编号、名称、专业、状态和资料入口元数据；不复制条文全文。
- `cad_interpret` 增强编号归一化与图集分类；修正 GB50854-2013 的专业归类。
- 保留既有低内存 CAD 扫描、按图框/楼层取数、结构算量流水线、证据台账和退出码机制。

## 0.2.3 — 2026-09-14

修文档与退出码，不加功能。

- 修正误导文案：入口闸只属于 `read_cad.sh`/`convert_dwg.sh` 全量路径；`cad_scan.sh` 快速路径不设体积闸。
- `cad_scan` 结果不完整时改为退出码 4，避免批量脚本把残缺量当完整量。
- 报告顶栏告警扩展到全部数据缺失类型。

## 0.2.2 — 2026-09-14

发布页文案与版本说明修正。

## 0.2.0 — 2026-09-14

按楼层取数与结果可核对。

- 新增 `--floor-label` 按图名只统计目标楼层图框。
- 每条文字带图层名，支持集中标注/原位标注归属和 `--detail-json` 全量台账。
- 图框编号与坐标范围可复现，截断显式告警。

## 0.28.0 — 2026-10-12（运行时自动自举 + 显式依赖底座）

- 新增 `scripts/ensure_runtime.sh`：任意 `run_cad.sh` 入口启动时先自检 vendor（ezdwg/ezdxf/fontTools），齐全则跳过、不联网；缺失时默认自动调 `install_vendor.sh` 从 GitHub Release 补齐。
- `CAD_AUTO_SETUP=0` 可关闭自动下载，给出明确手动安装指引；`install_vendor.sh` 的 curl 增加 `--max-time`（默认 600 秒）。
- 三个算量 skill（土建/安装/装饰）将改为显式依赖本底座：安装任一算量 skill 时自动检测并补齐 cad-file-reader，无需用户手动安装；仍保留 `SKILL_NO_BASE=1` 降级路径（离线/只用已有扫描与表格）。
- 验证：本机完整包 vendor 已存在（幂等跳过）；缺失 vendor 时自动下载路径经 dry-run 核对 Release 命名。

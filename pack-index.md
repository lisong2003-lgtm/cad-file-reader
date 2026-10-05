# 技能路由索引

## 默认入口

| 需求 | 读取 | 入口 |
|---|---|---|
| 大图快速读取、关键词、编号、图框 | `SKILL.md` | `scripts/cad_scan.sh` |
| 小图实体树、SVG、整树统计 | `SKILL.md` | `scripts/read_cad.sh` |
| DWG 转 DXF / 批量转换 | `SKILL.md` | `scripts/convert_dwg.sh` |
| 说明、构件规则、规范引用初解 | `SKILL.md` | `scripts/cad_interpret.sh` |
| 规范/图集元数据与输入缺口 | `SKILL.md` | `scripts/cad_normative.sh` |
| 装饰识图、房间/洞口/做法候选、投影校验 | `packs/descriptive-geometry/SKILL.md` | `scripts/cad_descriptive_geometry.sh` |
| 安装识图、系统/路由/设备/立管候选、竖向路由、系统拓扑、连通性审计 | `packs/mep-geometry/SKILL.md` | `scripts/cad_mep_geometry.sh` |
| 结构识图、梁/板/柱/墙/基础/楼梯/洞口/配筋/编号/节点/轴网候选、证据坐标 | `packs/structural-geometry/SKILL.md` | `scripts/cad_structural_geometry.sh` |
| 总图/场地识图、红线/道路/停车/挡墙/边坡/管线/标高/桩号/坐标候选、证据坐标 | `packs/site-geometry/SKILL.md` | `scripts/cad_site_geometry.sh` |
| 给排水/暖通深化识图、管道/风管/设备/支吊架/管径/标高/编号候选、证据坐标 | `packs/hvac-plumbing-geometry/SKILL.md` | `scripts/cad_hvac_plumbing_geometry.sh` |
| 精装修/室内深化识图、饰面/做法/材料/标高/节点候选、证据坐标 | `packs/interior-finish-geometry/SKILL.md` | `scripts/cad_interior_finish_geometry.sh` |
| 幕墙专业识图、立柱/面板/开启/埋件/分格/标高候选、证据坐标 | `packs/curtain-wall-geometry/SKILL.md` | `scripts/cad_curtain_wall_geometry.sh` |
| 人防工程识图、防护门/通风/电气/洗消/抗力等级/标高候选、证据坐标 | `packs/civil-defense-geometry/SKILL.md` | `scripts/cad_civil_defense_geometry.sh` |
| 预制装配深化识图、预制构件/预埋/连接/编号/桁架筋候选、证据坐标 | `packs/precast-geometry/SKILL.md` | `scripts/cad_precast_geometry.sh` |
| 电气识图、系统/路由/回路/设备/规格/防雷接地/消防/弱点/智能化候选、证据坐标 | `packs/electrical-geometry/SKILL.md` | `scripts/cad_electrical_geometry.sh` |
| 钢结构识图、构件/截面/连接/材料/涂装/节点候选、几何与连通性 | `packs/steel-geometry/SKILL.md` | `scripts/cad_steel_geometry.sh` |
| 市政专业识图、道路/桥隧/管网构件、材料、桩号/标高/坐标候选、几何与连通性 | `packs/municipal-geometry/SKILL.md` | `scripts/cad_municipal_geometry.sh` |
| 长度/面积/体积测量候选、比例单位校验、计算式与证据 | `packs/measurement-candidates/SKILL.md` | `scripts/cad_measure.sh` |
| 图层/块语义、块实例关联、低内存上限控制 | `SKILL.md` | `scripts/cad_semantics.sh` |
| 图纸变化对比、图层/块/文字/几何增删与移动 | `SKILL.md` | `scripts/cad_compare.sh` |
| 本机真实 DWG 回归（电气/消防/弱点/智能化/结构/总图场地/给排水暖通/精装修/人防/幕墙/预制装配）、真图清单脱敏复核 | `SKILL.md` | `scripts/run_real_dwg_regression.sh` |
| 统一候选契约、置信度分层、复核原因、交接 JSON 校验 | `SKILL.md` | `scripts/cad_validate.sh` |

## 资源

- `CAPABILITIES.md`：能力与边界索引；先读主入口，不必默认展开历史细节。
- `packs/mep-geometry/rules.json`：安装专业识图规则；只保存识别模式和证据边界。
- `packs/hvac-plumbing-geometry/rules.json`：给排水/暖通深化识图规则；只保存识别模式和证据边界。
- `packs/interior-finish-geometry/rules.json`：精装修/室内深化识图规则；只保存识别模式和证据边界。
- `packs/curtain-wall-geometry/rules.json`：幕墙识图规则；只保存识别模式和证据边界。
- `packs/civil-defense-geometry/rules.json`：人防工程识图规则；只保存识别模式和证据边界。
- `packs/precast-geometry/rules.json`：预制装配深化识图规则；只保存识别模式和证据边界。
- `packs/structural-geometry/rules.json`：结构识图规则；只保存识别模式和证据边界。
- `packs/site-geometry/rules.json`：总图/场地识图规则；只保存识别模式和证据边界。
- `packs/electrical-geometry/rules.json`：电气专业识图规则；只保存识别模式和证据边界。
- `packs/steel-geometry/rules.json`：钢结构识图规则；只保存识别模式和证据边界。
- `packs/municipal-geometry/rules.json`：市政专业识图规则；只保存识别模式和证据边界。
- `packs/measurement-candidates/SKILL.md`：测量候选契约、比例单位规则和专项算量交接。
- `schemas/candidate-v0.schema.json`：统一候选 JSON Schema；识图与测量输出先经 `scripts/cad_validate.sh` 校验。
- `rules/standards.json`：规范/图集元数据、版本状态和资料入口；不保存全文。
- `scripts/tests/`：识图行为回归；改动提取或报告逻辑后运行相关测试。

> 结构混凝土/钢筋算量、梁板柱墙算量流水线已迁到 tujian-suanliang（本机目录 shangwu-suanliang）。本技能不再路由 quantity-pipeline。

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
| 钢结构识图、构件/截面/连接/材料/涂装/节点候选、几何与连通性 | `packs/steel-geometry/SKILL.md` | `scripts/cad_steel_geometry.sh` |
| 市政专业识图、道路/桥隧/管网构件、材料、桩号/标高/坐标候选、几何与连通性 | `packs/municipal-geometry/SKILL.md` | `scripts/cad_municipal_geometry.sh` |
| 长度/面积/体积测量候选、比例单位校验、计算式与证据 | `packs/measurement-candidates/SKILL.md` | `scripts/cad_measure.sh` |

## 资源

- `CAPABILITIES.md`：能力与边界索引；先读主入口，不必默认展开历史细节。
- `packs/mep-geometry/rules.json`：安装专业识图规则；只保存识别模式和证据边界。
- `packs/steel-geometry/rules.json`：钢结构识图规则；只保存识别模式和证据边界。
- `packs/municipal-geometry/rules.json`：市政专业识图规则；只保存识别模式和证据边界。
- `packs/measurement-candidates/SKILL.md`：测量候选契约、比例单位规则和专项算量交接。
- `rules/standards.json`：规范/图集元数据、版本状态和资料入口；不保存全文。
- `scripts/tests/`：识图行为回归；改动提取或报告逻辑后运行相关测试。

> 结构混凝土/钢筋算量、梁板柱墙算量流水线已迁到 tujian-suanliang（本机目录 shangwu-suanliang）。本技能不再路由 quantity-pipeline。

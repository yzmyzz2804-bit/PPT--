---
name: cad-massing-to-sketchup
description: Parse a CAD 强排总图 DXF into building footprints and floor counts, then generate an editable SketchUp Ruby script that builds a clean clay-style massing model with glass volume, floor slabs and parapet. Use when the user provides DXF or 强排图 and wants 体块模型 or SU模型. Do not use for STL output or general CAD cleanup.
---

# CAD 强排总图 → SketchUp 体块模型

把用户的强排总图 DXF 转成**可编辑的 SketchUp 原生模型**（玻璃体 + 楼板 + 女儿墙的塑模状态体块）。输出是 `.rb` 生成脚本，在 SketchUp 内运行一次即得到原生几何（非网格、无 STL）。

## 硬性约定

- 只接受 **DXF**。用户给的是 DWG 时，先让他在 CAD 里另存为 DXF（2000 及以上任意版本均可），不要尝试解析 DWG。
- **层数**来自 DXF 内文字标注（如 `11F`、`18层`）；**层高**永远通过对话向用户确认，不允许虚构或套默认值不告知。
- 输出物只有 SketchUp Ruby 脚本（`.rb`）+ 运行说明。绝不产出 STL/OBJ/三角网格。
- 几何必须干净（塑模状态）：每栋一个 Group，内部按"玻璃体 / 楼板 / 女儿墙"三个子组 + 对应 Tag，纯堆叠原生面，无布尔、无余线、无构造点。脚本已保证，不要二次加工。

## 固定参数规则（已内置脚本默认值）

| 项目 | 规则 |
|------|------|
| 女儿墙 | 1.5 m；单层建筑（层数=1）为 1.0 m |
| 楼板厚度 | 层高 ≤ 5 m → 0.6 m；层高 > 5 m → 0.7 m |
| 楼板位置 | 每层顶部；顶层楼板即屋面板，女儿墙立于屋面板上 |
| 女儿墙厚度 | 0.2 m（沿轮廓内偏） |
| 底部 | 玻璃体从 ±0.000 起始，不设基座楼板 |

用户在对话中给出不同数值时，用命令行参数覆盖，并向他复述最终生效的参数表。

## 执行流程

### 1. 对话确认（生成前一次性问清）

1. 默认层高是多少（如住宅 3.0 m）；是否有按栋覆盖（如商业裙房 4.5 m），写成 `栋号=层高` 清单。
2. 是否有不生成体块的轮廓（保留绿地/道路等）。

### 2. 解析 DXF

```
python scripts/parse_dxf.py --dxf <总图.dxf> --out buildings.json
```

可选：`--unit mm|m|auto`（默认 auto：INSUNITS 优先，其次按轮廓尺度推断 mm/m）、`--min-area 20`（小于该面积的闭合轮廓视为杂线丢弃）、`--layers 图层1,图层2`（只取指定图层）、`--margin 5`（文字归属搜索半径）。

解析完成后必须向用户复述：
- 推断的单位（`units_assumed`）——mm 自动转 m；
- 楼栋清单表：编号 / 标注文字 / 图层 / 面积 m² / 层数 / 状态；
- `needs_review` 里的楼栋（轮廓旁没找到层数文字）——逐栋向用户要层数，**不要跳过**；
- `unmatched_texts` 里疑似层数但没归上轮廓的文字，请用户判断。

用户确认/补齐后，直接编辑 `buildings.json` 写入层数，再进入下一步。

### 3. 生成 SketchUp 脚本

```
python scripts/gen_su_script.py --buildings buildings.json --floor-height 3.0 --out massing_builder.rb
```

- `--floor-height`：对话确认的默认层高（米）。
- `--fh B03=4.5`（可多次）：按栋覆盖层高。
- `--parapet 1.5` `--parapet-single 1.0` `--slab-thin 0.6` `--slab-thick 0.7` `--parapet-thickness 0.2`：覆盖固定参数。
- `--name B01=1#住宅`（可多次）：给楼栋起显示名。
- 存在 `floors` 为 null 的楼栋时脚本会报错退出并列出栋号——先回步骤 2 补齐。

### 4. 交付运行说明（原文转述给用户）

1. 打开 SketchUp → 菜单"窗口 → Ruby 控制台"；
2. 输入 `load "E:/.../massing_builder.rb"`（正斜杠路径），回车；
3. 自动生成全部体块并缩放至全图，弹窗提示"N 栋完成"；
4. `文件 → 另存为` 保存 `.skp`，之后即可正常编辑。

可编辑性说明：每栋是一个命名 Group（如 `B01-11F`），Outliner 里能看到"玻璃体 / 楼板 / 女儿墙"三个子组；窗口 → 管理/默认面板 → 标记（Tags）里有同名三个 Tag 可控制显隐。想要白模效果，切换"视图 → 面板样式 → 消隐/单色"即可。

## 环境依赖

Python 3.x + `ezdxf`（缺失时 `python -m pip install ezdxf`）。脚本只依赖 ezdxf 标准接口。

## 详细规则与排错

堆叠 z 值公式、材质与 Tag 定义、弧线轮廓分段、单位误判、文字抓取失败等见 [references/geometry_rules.md](references/geometry_rules.md)。修改任何脚本后必须先用临时样例 DXF 跑通再交付。

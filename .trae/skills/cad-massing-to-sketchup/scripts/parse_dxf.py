#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""parse_dxf.py — 从强排总图 DXF 提取建筑闭合轮廓与层数标注，输出 buildings.json

用法:
    python parse_dxf.py --dxf 总图.dxf --out buildings.json [--unit auto|mm|m]
                        [--scale 1.0] [--min-area 20] [--layers 图层1,图层2]
                        [--text-layers 图层A,图层B] [--margin 5]

规则:
- 闭合 LWPOLYLINE / 2D POLYLINE 视为轮廓候选，面积 >= --min-area 才算楼栋；
- bulge 圆弧段自动展开为折线（约 7.5° 一段）；
- 层数从 TEXT/MTEXT 文字中抓取（如 11F / 18层 / 3f），归属到 bbox 外扩 --margin 米
  范围内、距质心最近的轮廓；
- 单位: --unit 指定优先；否则读 $INSUNITS；再否则按轮廓总尺度推断（>1000 视为 mm）。
输出 JSON 单位一律为米。
"""
import argparse
import json
import math
import re
import sys

import ezdxf

FLOOR_RE = re.compile(r"(\d+)\s*(?:F|f|层)")

INSUNITS_SCALE = {1: 0.0254, 2: 0.3048, 4: 0.001, 5: 0.01, 6: 1.0,
                  8: 0.0000254, 9: 0.000254, 10: 0.0254}


def parse_args():
    ap = argparse.ArgumentParser(description="强排总图 DXF → buildings.json")
    ap.add_argument("--dxf", required=True, help="DXF 文件路径")
    ap.add_argument("--out", required=True, help="输出 JSON 路径")
    ap.add_argument("--unit", choices=["auto", "mm", "m"], default="auto",
                    help="单位覆盖（默认 auto）")
    ap.add_argument("--scale", type=float, default=None,
                    help="额外缩放系数（最终坐标 = 原始坐标 * 单位比例 * scale）")
    ap.add_argument("--min-area", type=float, default=20.0,
                    help="楼栋最小面积 m²（默认 20，过滤杂线框）")
    ap.add_argument("--layers", default=None,
                    help="只取这些图层上的轮廓，逗号分隔（默认全部）")
    ap.add_argument("--text-layers", default=None,
                    help="只取这些图层上的文字，逗号分隔（默认全部）")
    ap.add_argument("--margin", type=float, default=5.0,
                    help="文字归属搜索外扩半径（米，默认 5）")
    return ap.parse_args()


def flatten_bulge(p1, p2, bulge, deg_step=7.5, max_seg=64):
    """把 p1→p2 之间带 bulge 的圆弧展开为中间点列（不含 p1/p2）。"""
    if abs(bulge) < 1e-9:
        return []
    theta = 4.0 * math.atan(bulge)  # 有向圆心角
    chord = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
    if chord < 1e-9:
        return []
    r = chord / (2.0 * math.sin(abs(theta) / 2.0))
    d = r * math.cos(abs(theta) / 2.0)
    ux, uy = (p2[0] - p1[0]) / chord, (p2[1] - p1[1]) / chord
    nx, ny = -uy, ux  # 弦方向左法线
    sgn = 1.0 if bulge > 0 else -1.0
    cx = (p1[0] + p2[0]) / 2.0 + sgn * d * nx
    cy = (p1[1] + p2[1]) / 2.0 + sgn * d * ny
    a1 = math.atan2(p1[1] - cy, p1[0] - cx)
    n = max(2, min(max_seg, int(math.ceil(abs(theta) / math.radians(deg_step)))))
    pts = []
    for i in range(1, n):
        a = a1 + theta * i / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def poly_from_entity(e):
    """返回闭合轮廓的 (x, y) 点列（含弧线展开）；非闭合返回 None。"""
    dxftype = e.dxftype()
    pts = []
    if dxftype == "LWPOLYLINE":
        if not e.closed:
            return None
        raw = e.get_points(format="xyb")
        n = len(raw)
        for i, (x, y, b) in enumerate(raw):
            pts.append((x, y))
            p2 = raw[(i + 1) % n]
            pts.extend(flatten_bulge((x, y), (p2[0], p2[1]), b))
    elif dxftype == "POLYLINE" and e.is_2d_polyline:
        if not e.closed:
            return None
        vs = [(v.dxf.location.x, v.dxf.location.y, v.dxf.bulge) for v in e.vertices]
        n = len(vs)
        for i, (x, y, b) in enumerate(vs):
            pts.append((x, y))
            p2 = vs[(i + 1) % n]
            pts.extend(flatten_bulge((x, y), (p2[0], p2[1]), b))
    else:
        return None
    # 首尾重复点去除
    if len(pts) >= 2 and abs(pts[0][0] - pts[-1][0]) < 1e-9 and abs(pts[0][1] - pts[-1][1]) < 1e-9:
        pts = pts[:-1]
    return pts if len(pts) >= 3 else None


def shoelace(pts):
    s = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return 0.5 * s


def bbox_of(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def collect_texts(msp, layer_filter):
    """返回 [(x, y, text), ...]，仅保留能解析出层数的文字。"""
    out = []
    for e in msp:
        if e.dxftype() == "TEXT":
            raw = e.dxf.text
            pos = e.dxf.insert
            if getattr(e.dxf, "halign", 0) or getattr(e.dxf, "valign", 0):
                pos = e.dxf.align_point
        elif e.dxftype() == "MTEXT":
            raw = e.plain_text()
            pos = e.dxf.insert
        else:
            continue
        if layer_filter and e.dxf.layer not in layer_filter:
            continue
        text = re.sub(r"\s+", "", str(raw))
        m = FLOOR_RE.search(text)
        if not m:
            continue
        out.append((pos.x, pos.y, text, int(m.group(1))))
    return out


def main():
    args = parse_args()
    try:
        doc = ezdxf.readfile(args.dxf)
    except Exception as exc:
        print(f"[错误] 无法读取 DXF: {exc}", file=sys.stderr)
        sys.exit(1)
    msp = doc.modelspace()

    layer_filter = None
    if args.layers:
        layer_filter = {s.strip() for s in args.layers.split(",") if s.strip()}
    text_layer_filter = None
    if args.text_layers:
        text_layer_filter = {s.strip() for s in args.text_layers.split(",") if s.strip()}

    # ---- 单位判定 ----
    all_pts = []
    open_plines = 0
    for e in msp:
        pts = poly_from_entity(e)
        if pts is None:
            if e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                open_plines += 1
            continue
        if layer_filter and e.dxf.layer not in layer_filter:
            continue
        all_pts.append(pts)
    if not all_pts:
        print("[错误] 没有找到闭合轮廓（可用 --layers 检查图层过滤条件）", file=sys.stderr)
        sys.exit(1)

    unit_name, unit_scale = "m", 1.0
    if args.unit == "mm":
        unit_name, unit_scale = "mm", 0.001
    elif args.unit == "m":
        unit_name, unit_scale = "m", 1.0
    else:
        try:
            insunits = int(doc.header.get("$INSUNITS", 0) or 0)
        except (TypeError, ValueError):
            insunits = 0
        if insunits in INSUNITS_SCALE:
            unit_scale = INSUNITS_SCALE[insunits]
            unit_name = {0.001: "mm", 1.0: "m"}.get(unit_scale, f"insunits={insunits}")
        else:
            extent = max(max(max(x for x, _ in pts) for pts in all_pts) - min(min(x for x, _ in pts) for pts in all_pts),
                         max(max(y for _, y in pts) for pts in all_pts) - min(min(y for _, y in pts) for pts in all_pts))
            unit_scale = 0.001 if extent > 1000 else 1.0
            unit_name = "mm(按尺度推断)" if unit_scale == 0.001 else "m(按尺度推断)"
    if args.scale:
        unit_scale *= args.scale

    # ---- 提取轮廓 ----
    buildings, seen = [], []
    for e in msp:
        if e.dxftype() not in ("LWPOLYLINE", "POLYLINE"):
            continue
        if layer_filter and e.dxf.layer not in layer_filter:
            continue
        raw_pts = poly_from_entity(e)
        if raw_pts is None:
            continue
        pts = [((x * unit_scale), (y * unit_scale)) for x, y in raw_pts]
        area = abs(shoelace(pts))
        if area < args.min_area:
            continue
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        # 简单去重：同图层、质心几乎一致、面积几乎一致
        dup = False
        for s in seen:
            if s["layer"] == e.dxf.layer and abs(s["cx"] - cx) < 0.01 and abs(s["cy"] - cy) < 0.01 \
                    and s["area"] > 0 and abs(s["area"] - area) / s["area"] < 0.01:
                dup = True
                break
        if dup:
            continue
        seen.append({"layer": e.dxf.layer, "cx": cx, "cy": cy, "area": area})
        buildings.append({
            "raw_layer": e.dxf.layer, "pts": pts, "area": area,
            "cx": cx, "cy": cy, "bbox": bbox_of(pts),
        })

    if not buildings:
        print(f"[错误] 没有面积 >= {args.min_area} m² 的闭合轮廓", file=sys.stderr)
        sys.exit(1)

    # ---- 层数文字归属（文字坐标同样换算到米）----
    texts = [(tx * unit_scale, ty * unit_scale, text, floors)
             for tx, ty, text, floors in collect_texts(msp, text_layer_filter)]
    pairs = []
    for ti, (tx, ty, text, floors) in enumerate(texts):
        for bi, b in enumerate(buildings):
            minx, miny, maxx, maxy = b["bbox"]
            if (minx - args.margin) <= tx <= (maxx + args.margin) and \
               (miny - args.margin) <= ty <= (maxy + args.margin):
                d = math.hypot(tx - b["cx"], ty - b["cy"])
                pairs.append((d, bi, ti))
    pairs.sort()
    assigned = {}
    used_texts = set()
    for d, bi, ti in pairs:
        if bi in assigned or ti in used_texts:
            continue
        assigned[bi] = ti
        used_texts.add(ti)

    out_buildings, needs_review = [], []
    for bi, b in enumerate(buildings):
        floors = None
        floors_text = ""
        if bi in assigned:
            tx, ty, floors_text, floors = texts[assigned[bi]]
        bid = f"B{bi + 1:02d}"
        out_buildings.append({
            "id": bid,
            "label": floors_text,
            "layer": b["raw_layer"],
            "floors": floors,
            "floors_text": floors_text,
            "area_m2": round(b["area"], 1),
            "centroid": [round(b["cx"], 3), round(b["cy"], 3)],
            "bbox": [round(v, 3) for v in b["bbox"]],
            "vertex_count": len(b["pts"]),
            "footprint": [[round(x, 4), round(y, 4)] for x, y in b["pts"]],
            "status": "ok" if floors else "needs_floors",
        })
        if not floors:
            needs_review.append(bid)

    unmatched = [
        {"text": t[2], "point": [round(t[0], 3), round(t[1], 3)]}
        for ti, t in enumerate(texts) if ti not in used_texts
    ]

    result = {
        "dxf": args.dxf,
        "units_assumed": unit_name,
        "unit_scale": unit_scale,
        "min_area_m2": args.min_area,
        "ignored_open_polylines": open_plines,
        "buildings": out_buildings,
        "needs_review": needs_review,
        "unmatched_texts": unmatched,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)

    print(f"[完成] 单位={unit_name} (scale={unit_scale}) | 楼栋={len(out_buildings)} "
          f"| 待补层数={len(needs_review)} | 未归属文字={len(unmatched)} "
          f"| 忽略未闭合多段线={open_plines}")
    for b in out_buildings:
        print(f"  {b['id']}  标注='{b['label']}'  图层={b['layer']}  "
              f"面积={b['area_m2']}m²  层数={b['floors']}  状态={b['status']}")
    if needs_review:
        print(f"[注意] 以下楼栋未抓到层数文字，请向用户确认后手填 floors 字段: "
              f"{', '.join(needs_review)}")


if __name__ == "__main__":
    main()

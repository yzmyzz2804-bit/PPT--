#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_su_script.py — 从 buildings.json 生成 SketchUp 原生体块 Ruby 脚本

用法:
    python gen_su_script.py --buildings buildings.json
                            --floor-heights "7,5.4,5.4"
                            --out massing_builder.rb
                            [--fhs B01=4.5,4.5 ...] [--name B01=1#厂房 ...]
                            [--parapet 1.5] [--parapet-single 1.0]
                            [--slab-thin 0.6] [--slab-thick 0.7]
                            [--parapet-thickness 0.2]

也支持统一层高: --floor-height 3.0 （等价于 --floor-heights "3.0" x N）
按栋覆盖: --fh B03=4.5 （统一层高）或 --fhs B03=7,5.4,5.4 （逐层）

几何堆叠规则（每栋, 逐层层高 fhs[], 逐层板厚 ts[]）:
- 第 i 层玻璃体:  z = sum(fhs[0..i-1]) → z + fhs[i] - ts[i]
- 第 i 层楼板:    z = z_i + fhs[i] - ts[i] → z_i + fhs[i]   (顶层楼板即屋面板)
- 女儿墙:         z = sum(fhs) 起, 高 hp, 沿轮廓内偏 pw 的墙体
- 单层建筑 hp = 1.0m, 其余 1.5m; 每层层高<=5m 时板厚 0.6m, >5m 时 0.7m

生成的 .rb 在 SketchUp 中 `load` 运行，得到按栋分组的原生几何（非网格）。
"""
import argparse
import json
import sys
from datetime import datetime

IN_M = 1.0 / 0.0254  # 1 米 = 39.370... 英寸（SU 内部单位）


def parse_kv_args(items, what):
    out = {}
    for it in items or []:
        if "=" not in it:
            print(f"[错误] {what} 参数格式应为 栋号=值，收到: {it}", file=sys.stderr)
            sys.exit(1)
        k, v = it.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def parse_args():
    ap = argparse.ArgumentParser(description="buildings.json → SketchUp .rb")
    ap.add_argument("--buildings", required=True, help="parse_dxf.py 输出的 JSON")
    ap.add_argument("--out", required=True, help="输出的 .rb 路径")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--floor-height", type=float,
                       help="统一层高（米），如 3.0；自动复制 N 份")
    group.add_argument("--floor-heights", help="逐层层高（米），逗号分隔，如 \"7,5.4,5.4\"")
    ap.add_argument("--fh", action="append", default=[],
                    help="按栋覆盖统一层高，如 --fh B03=4.5（可多次）")
    ap.add_argument("--fhs", action="append", default=[],
                    help="按栋覆盖逐层层高，如 --fhs B01=7,5.4,5.4（可多次）")
    ap.add_argument("--name", action="append", default=[],
                    help="按栋设置显示名，如 --name B01=1#厂房（可多次）")
    ap.add_argument("--parapet", type=float, default=1.5, help="女儿墙高（默认 1.5m）")
    ap.add_argument("--parapet-single", type=float, default=1.0,
                    help="单层建筑女儿墙高（默认 1.0m）")
    ap.add_argument("--slab-thin", type=float, default=0.6,
                    help="层高<=5m 的楼板厚（默认 0.6m）")
    ap.add_argument("--slab-thick", type=float, default=0.7,
                    help="层高>5m 的楼板厚（默认 0.7m）")
    ap.add_argument("--parapet-thickness", type=float, default=0.2,
                    help="女儿墙厚（默认 0.2m）")
    ap.add_argument("--project", default="", help="项目名（写进脚本注释）")
    return ap.parse_args()


def fmt(v):
    return f"{v:.6f}".rstrip("0").rstrip(".")


def main():
    args = parse_args()
    with open(args.buildings, encoding="utf-8") as f:
        data = json.load(f)
    buildings = data.get("buildings", [])
    if not buildings:
        print("[错误] buildings.json 里没有楼栋", file=sys.stderr)
        sys.exit(1)

    missing = [b["id"] for b in buildings if not b.get("floors")]
    if missing:
        print(f"[错误] 以下楼栋缺层数，先回 parse 步骤向用户确认并填入 floors: "
              f"{', '.join(missing)}", file=sys.stderr)
        sys.exit(2)

    fh_over = {k: float(v) for k, v in parse_kv_args(args.fh, "--fh").items()}
    fhs_over = parse_kv_args(args.fhs, "--fhs")
    name_over = parse_kv_args(args.name, "--name")

    # 全局逐层层高
    if args.floor_heights:
        global_fhs = [float(x) for x in args.floor_heights.split(",")]
    else:
        global_fhs = None  # 使用 --floor-height 时按各栋层数复制

    specs = []
    for b in buildings:
        bid = b["id"]
        n = int(b["floors"])
        if n <= 0:
            print(f"[错误] {bid} 层数非法: n={n}", file=sys.stderr)
            sys.exit(1)
        # 确定逐层层高列表
        if bid in fhs_over:
            fhs = [float(x) for x in fhs_over[bid].split(",")]
        elif bid in fh_over:
            fhs = [fh_over[bid]] * n
        elif global_fhs:
            fhs = global_fhs
        else:
            fhs = [args.floor_height] * n
        # 校验
        if len(fhs) != n:
            print(f"[错误] {bid} 层数={n} 但层高列表长度={len(fhs)}: {fhs}",
                  file=sys.stderr)
            sys.exit(1)
        for i, fh in enumerate(fhs):
            if fh <= 0:
                print(f"[错误] {bid} 第{i+1}层层高非法: {fh}m", file=sys.stderr)
                sys.exit(1)
            if fh <= args.slab_thin:
                print(f"[错误] {bid} 第{i+1}层层高 {fh}m 不大于楼板厚 {args.slab_thin}m",
                      file=sys.stderr)
                sys.exit(1)
        # 逐层板厚
        ts = [args.slab_thin if fh <= 5.0 else args.slab_thick for fh in fhs]
        hp = args.parapet_single if n == 1 else args.parapet
        label = name_over.get(bid) or b.get("label") or f"{n}F"
        pts = b["footprint"]
        if len(pts) < 3:
            print(f"[错误] {bid} 轮廓点数不足", file=sys.stderr)
            sys.exit(1)
        specs.append({
            "name": f"{bid}-{label}", "n": n, "fhs": fhs, "ts": ts, "hp": hp,
            "pts": pts,
        })

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = []
    a = lines.append
    a("# encoding: UTF-8")
    a("# =============================================================")
    a("# 强排体块生成脚本 (cad-massing-to-sketchup)")
    if args.project:
        a(f"# 项目: {args.project}")
    a(f"# 生成时间: {ts}   源: {data.get('dxf', '-')}")
    a("# 规则: 女儿墙 1.5m(单层 1.0m) | 每层层高<=5m 板厚 0.6m, >5m 板厚 0.7m")
    if args.floor_heights:
        a(f"# 逐层层高: {args.floor_heights}m")
    else:
        a(f"# 统一层高: {args.floor_height}m")
    extra = []
    if fh_over:
        extra.append(f"fh覆盖: {fh_over}")
    if fhs_over:
        extra.append(f"fhs覆盖: {fhs_over}")
    if extra:
        a(f"# {' | '.join(extra)}")
    a("# 用法: SketchUp → 窗口 → Ruby 控制台 → load \"本文件路径\"")
    a("# =============================================================")
    a("module Tikuang")
    a("  IN = 1.0 / 0.0254")
    a("")
    a("  MATS = {")
    a('    "体块-玻璃"   => [176, 208, 228, 0.35],')
    a('    "体块-楼板"   => [238, 238, 238, 1.0],')
    a('    "体块-女儿墙" => [248, 248, 248, 1.0],')
    a("  }")
    a("")
    a("  def self.get_mat(model, name)")
    a("    rgb = MATS[name]")
    a("    m = model.materials[name]")
    a("    unless m")
    a("      m = model.materials.add(name)")
    a("      m.color = Sketchup::Color.new(rgb[0], rgb[1], rgb[2])")
    a("      m.alpha = rgb[3]")
    a("    end")
    a("    m")
    a("  end")
    a("")
    a("  def self.set_tag(ent, name)")
    a("    m = Sketchup.active_model")
    a("    ly = m.layers[name] || m.layers.add(name)")
    a("    if ent.respond_to?(:tags=)")
    a("      ent.tags = [name]")
    a("    else")
    a("      ent.layer = ly")
    a("    end")
    a("  rescue StandardError")
    a("  end")
    a("")
    a("  def self.paint(ents, mat_name)")
    a("    mat = get_mat(Sketchup.active_model, mat_name)")
    a("    ents.grep(Sketchup::Face).each do |f|")
    a("      f.material = mat")
    a("      f.back_material = mat")
    a("    end")
    a("  end")
    a("")
    a("  # 水平截面 pts(x,y 英寸) 在 z0 处建面并向上拉伸 h")
    a("  def self.prism(ents, pts, z0, h, mat_name)")
    a("    return if h <= 1.0e-6")
    a("    f = ents.add_face(pts.map { |p| Geom::Point3d.new(p[0], p[1], z0) })")
    a("    return if f.nil?")
    a("    f.reverse! if f.normal.z < 0")
    a("    f.pushpull(h)")
    a("    paint(ents, mat_name)")
    a("  end")
    a("")
    a("  # 女儿墙: 沿轮廓每条边向内偏 w 的墙体")
    a("  def self.walls(ents, pts, z0, h, w, mat_name)")
    a("    area2 = 0.0")
    a("    n = pts.length")
    a("    (0...n).each do |i|")
    a("      p1 = pts[i]")
    a("      p2 = pts[(i + 1) % n]")
    a("      area2 += p1[0] * p2[1] - p2[0] * p1[1]")
    a("    end")
    a("    ccw = area2 > 0")
    a("    (0...n).each do |i|")
    a("      p1 = pts[i]")
    a("      p2 = pts[(i + 1) % n]")
    a("      dx = p2[0] - p1[0]")
    a("      dy = p2[1] - p1[1]")
    a("      len = Math.sqrt(dx * dx + dy * dy)")
    a("      next if len < 0.02 * IN")
    a("      nx = ccw ? -dy / len : dy / len")
    a("      ny = ccw ? dx / len : -dx / len")
    a("      q = [[p1[0], p1[1]], [p2[0], p2[1]],")
    a("           [p2[0] + nx * w, p2[1] + ny * w], [p1[0] + nx * w, p1[1] + ny * w]]")
    a("      prism(ents, q, z0, h, mat_name)")
    a("    end")
    a("  end")
    a("")
    a("  # 单栋: 玻璃体/楼板逐层堆叠(逐层层高) + 屋顶女儿墙")
    a("  def self.build(model, b)")
    a("    grp = model.entities.add_group")
    a("    grp.name = b[:name]")
    a('    parts = {}')
    a('    { "玻璃体" => :glass, "楼板" => :slab, "女儿墙" => :parapet }.each do |nm, key|')
    a("      sg = grp.entities.add_group")
    a("      sg.name = nm")
    a("      set_tag(sg, nm)")
    a("      parts[key] = sg")
    a("    end")
    a("    pts = b[:pts]")
    a("    fhs = b[:fhs]")
    a("    ts = b[:ts]")
    a("    n = fhs.length")
    a("    z = 0.0")
    a("    n.times do |i|")
    a("      fh = fhs[i]")
    a("      t = ts[i]")
    a('      prism(parts[:glass].entities, pts, z, fh - t, "体块-玻璃")')
    a('      prism(parts[:slab].entities, pts, z + fh - t, t, "体块-楼板")')
    a("      z += fh")
    a("    end")
    a("    walls(parts[:parapet].entities, pts, z, b[:hp], b[:pw], \"体块-女儿墙\")")
    a("    grp")
    a("  end")
    a("")
    a("  def self.run")
    a("    model = Sketchup.active_model")
    a('    model.start_operation("生成强排体块", true)')
    a("    begin")
    a("      BUILDINGS.each { |b| build(model, b) }")
    a("      model.commit_operation")
    a("    rescue StandardError => e")
    a("      model.abort_operation")
    a('      UI.messagebox("体块生成失败: #{e.message}")')
    a("      raise")
    a("    end")
    a("    model.active_view.zoom_extents")
    a('    UI.messagebox("体块生成完成: #{BUILDINGS.size} 栋")')
    a("  end")
    a("")
    a("  BUILDINGS = [")
    for s in specs:
        fhs_str = ", ".join(f"{fmt(fh)} * IN" for fh in s["fhs"])
        ts_str = ", ".join(f"{fmt(t)} * IN" for t in s["ts"])
        a(f"    # {s['name']}: {s['n']}层, 层高 [{', '.join(str(fh) for fh in s['fhs'])}]m, "
          f"板厚 [{', '.join(str(t) for t in s['ts'])}]m, "
          f"女儿墙 {s['hp']}m x {args.parapet_thickness}m")
        a("    { name: \"%s\", fhs: [%s], ts: [%s], hp: %s * IN, pw: %s * IN,"
          % (s["name"], fhs_str, ts_str, fmt(s["hp"]), fmt(args.parapet_thickness)))
        a("      pts: [")
        pts = s["pts"]
        for i in range(0, len(pts), 4):
            chunk = pts[i:i + 4]
            a("        " + ", ".join("[%s, %s]" % (fmt(x * IN_M), fmt(y * IN_M))
                                      for x, y in chunk) + ",")
        a("      ] },")
    a("  ]")
    a("end")
    a("")
    a("Tikuang.run")

    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    print(f"[完成] 已生成 {args.out}（{len(specs)} 栋）")
    print("参数生效表: 女儿墙 %.2f m (单层 %.2f m) | 楼板 %.2f m (层高<=5m) / %.2f m (层高>5m)"
          % (args.parapet, args.parapet_single, args.slab_thin, args.slab_thick))
    for s in specs:
        total = sum(s["fhs"]) + s["hp"]
        fhs_str = ", ".join(f"{fh}" for fh in s["fhs"])
        print(f"  {s['name']}: {s['n']}层 [{fhs_str}]m → 总高 {total:.2f}m (含女儿墙)")


if __name__ == "__main__":
    main()

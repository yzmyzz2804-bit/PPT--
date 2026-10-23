#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_rb.py — 对 gen_su_script.py 生成的 .rb 做静态自检（不依赖 Ruby）

用法: python check_rb.py massing_builder.rb

检查项:
1. 首个非空行必须是 `# encoding: UTF-8`
2. `module` 之前不允许出现非注释代码行（曾因注释内嵌换行丢失 # 前缀出过语法错误）
3. 去掉注释与字符串字面量后 def/begin/do/if/unless/module 与 end 数量配对
4. 关键调用齐全（start_operation / commit_operation / pushpull 等）
"""
import re
import sys

path = sys.argv[1]
src = open(path, encoding="utf-8").read()
lines = src.splitlines()

first = next(l for l in lines if l.strip())
assert first.startswith("# encoding: UTF-8"), f"首行编码声明缺失: {first!r}"

for l in lines:
    s = l.strip()
    if s.startswith("module "):
        break
    assert s == "" or s.startswith("#"), f"module 前出现代码行: {l!r}"

code = "\n".join(l for l in lines if not l.lstrip().startswith("#"))
code = re.sub(r'"[^"]*"', '""', code)
openers = (
    len(re.findall(r"\bdef\b", code))
    + len(re.findall(r"\bbegin\b", code))
    + len(re.findall(r"\bdo\s*(\|[^|]*\|)?\s*$", code, re.M))
    + len(re.findall(r"^\s*(?:if|unless|module|class)\b", code, re.M))
)
ends = len(re.findall(r"^\s*end\s*$", code, re.M))
print(f"openers={openers} ends={ends}")
assert openers == ends, "块配对不平衡"

for token in ["module Tikuang", "BUILDINGS = [", "Tikuang.run",
              "start_operation", "commit_operation", "zoom_extents",
              "Geom::Point3d.new", "pushpull"]:
    assert token in code, f"缺少 {token!r}"
print("check_rb: ALL OK")

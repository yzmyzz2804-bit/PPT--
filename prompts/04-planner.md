# 方案与共同内容模型
输入：已核claims、批准constraints；输出：options.json（2–3种）→ selection.json → deck.json、outline.md、page_plan.md、materials.md。
方案描述主线、用途、权衡、受保护变更范围；不可先修改受保护内容。selection绑定options SHA并经人工批准。
先整册大纲，再逐页核心信息和claim_id，再拆物料，最后交渲染；保留用户⑤⑥⑦为三类交付物，而非倒序执行。
每页一个核心信息任务；封面/目录可无图；不要为了“一页一图”捏造图表。汇报/打印页数可以不同，用source_page_ids建立映射。
deck绑定claims/constraints/selection当前SHA，所有关键主张必须在每个请求版本有可追溯呈现。打印可多解释，不改事实。
涉及结构重排、图片替换、既有分析重做、纠错和版式改造：在03_content/changes/写独立提案，deck.protected_change_refs绑定提案前后哈希与scope；先批再执行。
内容模型人工批准后才调用渲染角色。禁止临时“润色”改变已批结论。

v7强制：遵守WORKBENCH_RULES_V7.md及L01—L09对象门控；生产渲染前必须生成并校验03_content/object_layout.json。禁止固定几何切块。无法重建对象标unresolved/reference，不当作pass。

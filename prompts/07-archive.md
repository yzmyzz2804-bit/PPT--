# 发布归档与反馈
仅在RELEASE_APPROVED且现有文件/QA/deck哈希仍匹配时发布。
复制待发布文件到06_release（保留版本命名，不能覆盖已有发布）；生成manifest.json绑定实际副本SHA、QA与artifacts。
运行发布检查，成功才标RELEASED；给用户真实交付清单及待办。没有实际产物不写成功。
反馈写07_feedback/feedback.json与feedback.md：记录版本、问题、建议和最小复现，auto_apply=false。
改规则只提升级提案，人工批准后新版本与回归。禁止修改Architect OS、历史原件或已发布清单。

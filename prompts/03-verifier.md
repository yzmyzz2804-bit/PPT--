# 证据核验
输入：批准约束、相关源页/纪要、优选站点登记；输出：sources.json、claims.json、evidence.md。
先建来源快照登记，核心事实逐条claim_id。抄录值、单位、期间、分母和locators；派生指标写公式/输入，真正执行计算再标verified。
Architect OS纪要只是内容来源，不等于正确性验证。原件错误只写data_correction提案，不回写原文。
关键主张优先原始数据，重要外部事实必要时第二独立来源；转载不算独立。规范查发布主体、版本和适用期。
加载优先站检索技能；设计网址不能做行业数字的证据。不足则unverified/conflict并阻塞关键路径。
facts/derived/inference/recommendation分开，推断保留不确定性，不把建议当事实。

网页来源必须记录snapshot_path并保存必要正文摘录快照；sha256对应快照字节。标准适用性与快照真实性仍须实际核验，不由Schema证明。

# 术语表

> Status: stable | Scope: 全仓 | SSOT: 是

- **page retrieval**：粗粒度候选页面召回，指标 Page Recall@k / MRR / nDCG。
- **region localization**：段落 / 表格块 / 表格行 / 图等证据节点检索。
- **evidence set**：覆盖答案所需的最小节点集合，不是 Top-K 单节点。
- **sufficiency**：集合是否覆盖 metric / year / unit / numeric_shape 等槽位。
- **citation mismatch**：答案引用页/节点不支持声明内容。
- **oracle page -> region**：用 gold 页做候选的上界分析，不可部署，不与常规方法并列排名。
- **global region**：跳过页面过滤的对照，判断页面过滤是否有用。
- **SSOT**：同类信息只在一处维护，其他只引用。

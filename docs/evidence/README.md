# 研发与技术证据页

公开入口：https://nighty35628.github.io/ligand-screening/evidence.html

本页为黑客松补充材料：分析流程、模型与Agent编排、混凝土完整运行实例、五个案例、科研探索和工程交付记录。页面中每个主要结论均链接到代码或已有结果。它不发起训练或API请求。

## 文件

- `page-template.html`：页面文案、布局和可视化代码。
- `research-records.md`：按实际研究报告、产物与提交整理的研发历程。
- `research-excerpts.md`：八份早期报告节选，保留原档案路径和SHA256；未公开整个工作区。
- `sciencepal-results.md`、`sciencepal-check.json`：SciencePal方法研究结果与本机独立实现的数值复算。
- `../../amadeus/web/evidence.html`：生成后的页面，可在在线站点、本机工作台或直接打开文件查看。
- `../../amadeus/web/evidence-data.json`：图表数值与来源哈希。

重新生成：`python3 scripts/build_evidence_page.py`。该命令只读取保存的结果，生成图表输入和页面，不重新拟合。

页面生成后，如需部署，请更新 `amadeus/web-manifest.json` 中对应文件的SHA256；GitHub Pages会校验所有前端资产。

## 内容核查

混凝土散点来自171条已保存候选预测与公开标签；图表模型分数来自22组实际比较；候选MAE由保存值重新计算。科研历程区分前期探索、冻结比较、工程验收与比赛交付。双钙钛矿带隙标为计算标签；其他案例为公开实测。在线快照展示和本机计算能力分别说明。

页面不包含账号、密钥、私人对话原文或成员身份信息。SciencePal对话入口已在提交表其他栏目提供。

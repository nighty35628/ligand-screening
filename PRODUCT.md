# 配体优选

<!-- impeccable:product-schema 1 -->

## Platform
web

## Users
黑客松组员与评委，在电脑或手机上通过公开网页理解配体筛选方案。

## Product Purpose
演示如何从18个候选配体中安排有限的测试名额，理解两路模型如何形成推荐，并在之后揭晓已有实测结果、比较基线。

## Operating Context
GitHub Pages上的静态交互演示；可离线打开同一HTML。用户确认分步引导：开始分析、查看推荐、揭晓实测、查看对比。初始页面不得显示推荐结果、实测答案或整体效果数字。

## Capabilities and Constraints
使用固定90配体、15池、预算1—5的已验收数据，不重新训练模型、不修改算法或结果。浏览器可以真实复算名次与融合。进度动画提供演示节奏，不声称现场训练或新湿实验。方法细节统一收进一个入口，保留必要来源和证据范围。

## Brand Commitments
用户确认浅色、精致科研工具风格，留白充足，突出分子和曲线。保留配体优选名称。

## Evidence on Hand
`demo/final/data.json`及manifest为固定结果；`results/reference/`包含统一评价；原代码与数据来源在THIRD_PARTY.md。

## Product Principles
- 每阶段只有一个主要下一步。
- 初始无结果，推荐与实测逐步显示。
- 图形与结构承担解释，避免重复碎片说明。
- 全部候选池可访问，不挑优胜案例。

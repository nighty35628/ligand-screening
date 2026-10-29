# 数据、方法与第三方资源

本项目使用 ALLiS 公开档案并借鉴成对回归流程，保留来源而不声称这些资源由本项目原创。

- 数据与代码来源：[qai222/ALLiS](https://github.com/qai222/ALLiS/tree/1796d18496c669d554fa165a88d83e7b3cd9a905)，固定提交 `1796d18496c669d554fa165a88d83e7b3cd9a905`。
- 原始研究：[Active learning of ligands that enhance perovskite nanocrystal luminescence](https://doi.org/10.1021/acsnano.4c02094)，ACS Nano，2024。
- 原始数据文件 `reaction_collection_train_AL0503.json.gz` 的 SHA256：`69551e9f1b0e37a74df6089ca8e6e5db9f3560c0e2dac54e09e47634528c8241`。
- 42维描述符由原档案预计算提供；Morgan计数指纹与结构SVG为此前使用RDKit生成的派生产物，当前复算无需RDKit。
- 运行依赖：NumPy、SciPy、scikit-learn、joblib、threadpoolctl、cloudpickle；具体版本见 `requirements-allis.txt`。各依赖适用其自身许可。
- 浏览器验证使用Playwright与Chrome，不是应用运行依赖。

资产目录保留来源路径、配置、固定输入、预测及哈希，便于追溯。原始资料许可未在本次上传中重新作法律判定，本仓库不对原数据、原代码或派生产物作统一MIT等再许可声明。

本项目新增部分包括：固定等权的双模型排名融合、统一回顾性比较入口、保存加载预测、独立指标复算和交互回放界面。方法组合的适用效果由实际结果描述，不据此宣称全新算法原理或新材料发现。

## 通用表格工作流示例

`amadeus/web/sample-history.csv`（80行）与 `sample-candidates.csv`（12行）来自已有公开配方数据审计结果。按原 group 前80组/后续12组选取，历史与候选不共享group；候选文件去除目标peak。字段保留PbBr2、Cs-oleate、Aceton加入体积。用于功能演示，不作为本项目新增性能结论。

Lampe et al., *Rapid Data-Efficient Optimization of Perovskite Nanocrystal Syntheses through Machine Learning Algorithm Fusion*, DOI https://doi.org/10.1002/adma.202208772 。作者代码 https://github.com/benkour/Quantum_Dot_optimization ，审计固定提交 `659e2c37ec6cf11e3f972ca21e7b6745c49285a4`。

## 新材料表格验收数据

I-Cheng Yeh, Concrete Compressive Strength, UCI Machine Learning Repository, DOI [10.24432/C5PK67](https://doi.org/10.24432/C5PK67), CC BY 4.0。原始数据与标准化拆分位于 amadeus/examples/concrete；配方分组、字段改名和候选标签隔离为本项目处理。

## 钢合金案例

Matbench v0.1 matbench_steels，312种实验钢合金组成/屈服强度；数据来自Citrine，原始引用与元数据保存在 amadeus/examples/steels/source_metadata.json。Matbench参考：Dunn et al., npj Computational Materials 6, 138 (2020), DOI 10.1038/s41524-020-00406-3。组成描述与自定义划分是本项目处理；不作为官方Matbench成绩。

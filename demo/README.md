# 给组员的 ALLiS 融合演示

直接用浏览器打开 **index.html**。这是约 1.2 MB 的单文件演示，内含结构图、预测和既有答案，可以单独发给组员；无需 Python、安装依赖或联网。

项目目录也可运行 `./run_demo.sh`，然后访问 http://127.0.0.1:8765 。端口可通过 `ALLIS_DEMO_PORT` 设置。这个地址只在启动它的电脑上可用；给组员分享请发送 index.html。

## 讲解顺序

1. 保持默认首个候选池、预算 3，说明训练用 36 个配体，接下来在 18 个候选中选 3 个。
2. 点击候选查看真实二维结构、成对 ET 的用量曲线，以及直接评分 ET 的 Q 预测。Q 是 40 点中最高 4 点 FOM 的平均。
3. 看两路名次怎样等权平均，再比较下方三份推荐名单。融合的是名次，不是发光分数。
4. 点击“揭晓实测结果”，看实测曲线、每份名单选到的最佳 Q，以及预算 1—5 的对照曲线。
5. 看全部 15 池汇总，再切换其他池或预算。保留收益与退化情况，不以单个池证明有效。

## 来源与口径

- 来源是 `outputs/allis_retrain_verified` 的封存预测与评分；导出前检查其 delivery_seal 和 verification。
- 15 池、每池 18 候选，预算 1—5；推荐采用原回放 seed 42，恰好选 B 个。同分的正式评分使用精确均匀随机期望，页面与单次回放分开标注。
- 所有结果都是既有公开档案上的回顾性评估。隐藏答案仅为讲解交互，文件中已包含答案。
- 本次没有训练模型、增加机制、修改两路预测或权重。分子图通过 RDKit 从已存 SMILES 绘制，不参与模型。
- 默认池 r0_f0、预算 3，没有按实测结果挑默认池。15 池均可查看。

## 可复核文件

- `manifest.json`：来源封印哈希与页面、数据、样式和脚本哈希。
- `data.json`：导出的固定数据，方便审查。
- `qa/browser_verification.json`：离线真实 Chrome 交互核对，75 个池×预算状态、225 份名单、隐藏/揭晓、键盘操作及手机横向溢出。
- `qa/source_verification.json`：与封存源逐项比对，包含标签、预测、名次、固定回放选择及汇总。
- `qa/*png`：电脑隐藏/揭晓和手机揭晓截图。

维护页面时编辑 `template.html`、`style.css`、`app.js`，再用具有 RDKit、NumPy、SciPy 和现有项目依赖的 Python 执行 `demo/build_demo.py`。不需要重新拟合模型。浏览器核对脚本是 `qa/check_demo.cjs`，需要 Playwright 和 Chrome；通过 `PLAYWRIGHT_MODULE` 指定已安装的模块路径。

如果只更新界面，可执行 `.venv-allis/bin/python demo/build_demo.py --reuse-structures`，复用已校验哈希且 ID、SMILES 相符的结构图，不再需要 RDKit。源数据核对命令：`.venv-allis/bin/python demo/qa/check_source.py`。

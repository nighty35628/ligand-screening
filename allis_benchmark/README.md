# 配体优选：统一运行入口

这套入口完成随机选择、成对RF的均值／上界排序、成对ET、直接评分ET和固定等权融合的统一比较。旧 `allis_delivery` 和原资产保持不变。

## 直接运行

在项目根目录：

```bash
./run_project.sh
```

默认从已校验资产复算全部15池、六策略，新增拟合0次。自动创建新输出目录，含完整结果表、逐池CSV、预测、无标签候选输入和独立复算结果。首次使用自动沿用 `run_allis.sh` 安装锁定Python依赖；依赖就绪后不需要网络。

重训全部RF基线，ET组件复用已核验预测：

```bash
./run_project.sh run --mode baseline-retrain --output outputs/my_rf_reproduction
./run_project.sh verify --run-dir outputs/my_rf_reproduction
```

该模式15次新拟合，硬上限20次／1200秒，单池180秒。输出目录必须新建或为空。第一池兼作工程检查，满足同一协议后纳入全部15池，不根据输赢选择候选池。模型保存到 `models/*.joblib`，预测由重新加载的模型产生。缓存与重训模式分别记录，不把复用称为新训练。

两个ET组件的训练／预测／评估也通过同一个脚本转发：

```bash
# 一池两次拟合，工程核查
./run_project.sh models run --mode retrain --splits r0_f0 --output outputs/my_component_check

# 不提供 --splits 时为15池、30次拟合；这是单独明确调用的完整ET重训，
# 不包含在本轮17次拟合中。
```

## 保存模型预测候选

RF预测：

```bash
./run_project.sh predict --run-dir outputs/my_rf_reproduction --split r0_f0 \
  --candidates outputs/my_rf_reproduction/candidate_inputs/r0_f0.npz \
  --output outputs/my_rf_predictions.json
```

两路ET与融合预测：

```bash
./run_project.sh models predict --run-dir outputs/my_component_check --split r0_f0 \
  --candidates outputs/my_rf_reproduction/candidate_inputs/r0_f0.npz \
  --output outputs/my_fusion_predictions.json
```

候选NPZ只允许 `features`、`dose_pmol`、`ids`、`feature_names` 四个字段，禁止夹带答案。输入为N×2090结构特征（42维描述符＋2048维计数Morgan）与N×40正递增实际用量。RF仅使用前42维及训练内保留列；ET使用组合表示。身份不能与模型训练身份重叠。已有候选库的特征已提供；任意SMILES自动提取全部42维特征尚不在支持范围。

## 演示

直接打开 `demo/final/index.html`，或运行 `./run_demo.sh` 后访问打印的地址。页面离线包含固定预测和已有实测答案，揭晓只控制显示；模型实际训练和新特征预测使用上述CLI。演示支持全部15池、预算1—5、六种策略、两路预测、融合名次、RF曲线和实测曲线。

从一个完成的统一运行目录重新生成页面：

```bash
.venv-allis/bin/python demo/build_final_demo.py --run-dir outputs/my_rf_reproduction
```

## 冻结协议与结果边界

- `assets/protocol.json`：划分、模型、预算、特征、随机种子、来源和基线适配范围，执行前固定。
- 90种配体，每种40点；15池来自三套五折，36训练／18候选，未使用的另36种不提供标签。
- Q为最高4点相对PL FOM的均值。AUR为预算1—5下距离本池最优Q的平均差距。
- RF使用与成对ET相同的131072训练对、48树/depth16/leaf2，42维原描述符，线性实际用量。它是固定预算模型移植，不是完整原始主动学习和全对训练复现。
- RF上界由参照预测的标准误计算；参照并非独立测量，不声称置信覆盖校准。均值和上界两种规则均完整报告。
- 所有方法共享训练标签、候选池和推荐名额。输入表示有明确差异；融合与两个ET组件比较才能区分融合增益。
- 只做固定历史推荐，不在每揭晓一个配体后重新训练。训练预算不等同于实际实验时间／成本。
- 已有数据多轮用于探索，本次是工程复现和回顾性证据，不是新盲测。逐池正负结果均保留。

数据与原方法来源记录在 `assets/protocol.json` 及 `allis_delivery/assets/provenance.json`。主界面使用功能名称，资源来源仍可追溯。

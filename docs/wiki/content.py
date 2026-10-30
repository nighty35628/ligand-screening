"""Editable Wiki articles. Source references point to the actual project files."""
PAGES = []
def page(slug,title,group,description,sources,body):
    PAGES.append(dict(slug=slug,title=title,group=group,description=description,sources=sources,body=body))

page('', 'Amadeus 项目文档', '开始使用', '材料研究的数据分析与建模助手：从资料整理、材料表示，到模型验证、预测与报告。', ['README.md','amadeus/workflow.py'], '''
<div class="start-links"><a href="wiki:quickstart"><strong>开始使用</strong><span>在线体验、本机安装与首次运行</span></a><a href="wiki:data"><strong>接入自己的数据</strong><span>准备历史记录、候选表与字段映射</span></a><a href="wiki:models"><strong>理解模型</strong><span>通用回归与纳米晶双路预测</span></a><a href="wiki:development"><strong>参与开发</strong><span>接口、扩展方法、测试与部署</span></a></div>
<h2>Amadeus 做什么</h2><p>Amadeus把材料研究中的资料整理、数据分析和预测放在同一个项目里。你可以从一个研究问题、已有实验表或公开案例开始，整理可比较的记录，构造材料特征，比较模型，再查看候选预测和分析报告。</p><p>需要安排实验时，可以继续编辑名单、保存计划、记录结果，并将新增测量带入后续分析。结果回填是分析流程的延伸，不是每项研究的必选终点。</p>
<h2>输入与输出</h2><table><thead><tr><th>你提供</th><th>系统完成</th><th>你得到</th></tr></thead><tbody><tr><td>研究目标、文献正文或文本PDF</td><td>检索、信息提取与原文核对</td><td>来源记录、实验信息草稿和可编辑数据表</td></tr><tr><td>历史表、候选表、字段含义</td><td>数据检查、特征与模型比较</td><td>验证分数、候选预测、排名和报告</td></tr><tr><td>公开案例或已完成项目</td><td>加载模型／分析记录，展示对照</td><td>完整流程体验及可追溯结果</td></tr></tbody></table>
<h2>选择运行方式</h2><p><a href="site:">在线工作台</a>可直接体验五个案例，无需账号或API Key；它使用已完成的计算结果。本机版本运行实际数据处理、模型训练、固定模型推断和项目管理。联网对话、检索和文献提取需要配置DeepSeek接口。</p>
<h2>阅读路线</h2><ul><li>第一次使用：<a href="wiki:quickstart">快速开始</a> → <a href="wiki:guide">工作台使用指南</a> → <a href="wiki:cases">案例手册</a>。</li><li>带着自己的数据：<a href="wiki:data">数据规范</a> → <a href="wiki:features">材料表示</a> → <a href="wiki:validation">验证与指标</a>。</li><li>查看技术实现：<a href="wiki:architecture">系统架构</a> → <a href="wiki:api">接口与工具</a> → <a href="wiki:development">开发与部署</a>。</li></ul><p>比赛评审或快速了解研发成果，可阅读独立的<a href="site:evidence.html">研发与技术证据页</a>。研究历程、版本变化与资源归属收录在本站最后一个栏目。</p>
''')
page('quickstart','快速开始','开始使用','选择在线体验，或在本机启动完整工作台。',['run_amadeus.sh','.env.example','amadeus/provider.py','amadeus/server.py'],'''
<h2>在线体验</h2><ol><li>打开<a href="site:">Amadeus工作台</a>，选择一项研究。</li><li>纳米晶案例展示自动引导流程；混凝土、钢合金、带隙和热导率案例会预填内容，按照页面提示逐步操作。</li><li>查看模型分析与候选结果，保存计划，再揭晓公开参考值并生成报告。</li></ol><p>在线项目记录保存在当前浏览器。需要保留时下载项目或报告；清除站点存储、切换浏览器不会自动迁移记录。</p>
<h2>本机安装</h2><p>安装Git，以及uv或Python 3.12。首次运行会创建环境并安装<code>requirements-allis.txt</code>中的依赖。下列命令在终端执行。</p><pre><code>git clone https://github.com/nighty35628/ligand-screening.git
cd ligand-screening
./run_amadeus.sh</code></pre><p>打开 <a href="http://127.0.0.1:8787/">http://127.0.0.1:8787/</a>。数据导入、模型计算与图表操作可以通过工作台使用；联网功能按下一节配置。</p>
<h2>配置对话与检索</h2><pre><code>cp .env.example .env.local
# 用文本编辑器打开 .env.local，填写自己的服务配置
./run_amadeus.sh</code></pre><table><thead><tr><th>变量</th><th>作用</th></tr></thead><tbody><tr><td><code>DEEPSEEK_API_KEY</code></td><td>本机服务调用API所用凭据</td></tr><tr><td><code>DEEPSEEK_BASE_URL</code></td><td>服务地址，模板为 https://api.deepseek.com</td></tr><tr><td><code>DEEPSEEK_MODEL</code></td><td>对话模型标识，模板为 deepseek-flash；以账号可用模型为准</td></tr></tbody></table><p>配置由本机进程读取，同名环境变量优先于文件。密钥文件被Git忽略。对话、Search和Fetch的具体请求路径见<a href="wiki:api">接口与工具</a>。</p>
<h2>常用启动方式</h2><pre><code># 换一个本机端口
./run_amadeus.sh --port 8788

# 使用已有Python环境
AMADEUS_PYTHON=/absolute/path/to/python ./run_amadeus.sh</code></pre><p>工作台监听127.0.0.1。本机项目保存在<code>outputs/amadeus-workspace/</code>，重启后可以继续。遇到安装或接口问题，查看<a href="wiki:faq">常见问题</a>。</p>
''')
page('guide','工作台使用指南','开始使用','从问题、资料或实验表开始，完成一次可保存的分析。',['amadeus/web/workbench.js','amadeus/workflow.py'],'''
<h2>创建研究</h2><p>输入材料体系、想分析的性能，以及手头的数据。例：“我有混凝土配方与养护龄期记录，希望预测抗压强度并比较候选。”有自己的数据时，进入数据页上传历史表与候选表；只想体验时，直接选择首页研究案例。</p>
<h2>整理资料与字段</h2><p>正文和文本PDF先进入实验提取草稿。检查每条记录是否属于同一实验、数值与单位是否一致，再接受为实验表。数据页选择编号、目标、输入特征、分组与优化方向。目标列表示要预测的结果，不能同时选为输入特征。</p><p>在“资料与模型引擎”中查看缺失、重复和转换记录，按需要生成分子特征。详见<a href="wiki:data">数据规范</a>。</p>
<h2>运行与阅读模型分析</h2><p>运行模型比较后，先看验证方式和模型分数，再看候选预测。回归通常以MAE选择模型；候选排序按“越大越好”或“越小越好”执行。纳米晶使用双路名次融合，因此应按融合排名阅读，不能只按曲线分支的单个预测值重排。</p><p>公开案例默认使用已有结果。想重新计算，在本机引擎中主动运行建模；在线版保留冻结分析。</p>
<h2>保存计划与记录结果</h2><ol><li>调整测试名额、排除不可用候选，或指定名单。</li><li>保存本轮计划，让候选与分析版本对应。</li><li>填写实际结果，或显式选择公开案例的历史结果。带隙案例会标为计算参考值。</li><li>进入下一轮，已完成项会从待选名单中排除。表格工作流可将新增测量纳入重训。</li></ol><p>修改名额或排除候选只改变选择结果，不会自动改变已有模型预测。切换目标指标会开启新的分析记录。</p>
<h2>导出与继续工作</h2><p>研究报告汇总目标、模型、图表、计划及结果。浏览器打印可保存PDF，计划可导出CSV，项目可导出JSON。本机重开项目保留分析历史；在线端和本机端的项目存储各自独立。</p>
''')
page('data','数据格式与字段映射','数据与建模','准备历史表与候选表，定义目标、分组及单位。',['amadeus/tabular.py','amadeus/data_engine.py','amadeus/examples/concrete/mapping.json'],'''
<h2>历史表与候选表</h2><p>历史表包含已知结果，候选表包含待预测对象。两表需要相同的输入特征列；候选编号必须非空且唯一。回归引擎要求至少10条有标签历史记录与非空候选表。CSV首行使用唯一列名，当前CSV入口最多20,000行、300列。</p><p>下面仅演示格式，不代表可直接训练的数据量。</p><pre><code># training.csv
id,mix_group,cement,water,age_day,strength_mpa
history_1,mix_a,300,180,28,35.2
history_2,mix_a,300,180,90,43.1

# candidates.csv
id,mix_group,cement,water,age_day
candidate_1,mix_b,340,170,28</code></pre>
<h2>字段映射</h2><pre><code>{
  "id": "id", "target": "strength_mpa", "group": "mix_group",
  "features": ["cement", "water", "age_day"],
  "task": "regression", "direction": "max", "unit": "MPa",
  "feature_groups": {
    "composition": ["cement", "water"],
    "condition": ["age_day"]
  },
  "optimize": true, "search_trials": 4, "selection_metric": "mae"
}</code></pre><p><code>group</code>应表达需要一起保留的材料或配方身份，例如同配方不同龄期。编号、目标和分组列不进入输入特征。分组名称不能代替真实批次信息；如果数据只支持组成分组，就按组成解释验证结果。</p>
<h2>JSON与文献输入</h2><p>JSON接受非空对象数组，或包含<code>rows</code>／<code>records</code>的对象。带<code>reactions</code>数组的原始纳米晶档案走专用展平逻辑，分出样品、参照与空白。</p><p>文献正文及文本PDF由大模型提出记录，并为每个非编号字段提供原文片段。系统检查片段是否确实存在；它不能替代对实验归属、单位和数值含义的人工核对。扫描PDF需先提供OCR文本。超过8,000字符时分段提取，跨段关系在接受前检查。</p>
<h2>单位转换与缺失值</h2><p>数据处理保留原值及修改记录。现成转换包括μL/mL、pmol/nmol、小时/天、百分数/比例。配体用量的换算为 <code>amount_nmol = volume_ul × stock_um / 1000</code>；原液浓度不是最终溶液浓度或表面覆盖度。</p><p>数值缺失可在模型训练管线内用中位数填补；目标必须为有限数。异常值、重复记录是否合并应根据实验含义决定，数据审计本身不自动判定科学上的重复实验。</p>
<h2>可用模板</h2><p>仓库各案例的<code>training.csv</code>、<code>candidates.csv</code>、<code>mapping.json</code>和<code>data_dictionary.json</code>可用作格式参照。实际数据和字段说明位于<code>amadeus/examples/</code>。</p>
''')
page('features','材料表示与特征','数据与建模','分清通用结构特征、专用配体表示，以及材料组成特征。',['amadeus/data_engine.py','allis_delivery/core.py','scripts/prepare_steels.py','scripts/verify_unprepared_cases.py'],'''
<h2>结构导入的通用特征</h2><p><code>molecular_features</code>支持SMILES与以<code>InChI=</code>开头的结构。RDKit生成分子量、LogP、氢键供体数、氢键受体数、可旋转键数和TPSA，以及radius=2的128位Morgan二值指纹。结构解析失败会返回行号和原始字符串，对应特征留空。</p>
<h2>纳米晶专用模型表示</h2><p>冻结配体模型采用原42维描述符，加radius=2、2048维Morgan计数指纹。成对分支进一步使用两个测量点的表示及差值，并包含实际用量。它与通用导入工具的128位指纹是两套配置，不能直接互换模型输入。</p><p>分子指纹补充局部连接信息；描述符保留物化与拓扑概要。模型分数不直接等于已验证的配位机理，特征贡献需结合材料条件解释。</p>
<h2>材料组成与实验条件</h2><p>钢合金、带隙和热导率案例将化学式解析为归一化元素比例，并生成元素数、组成熵、平均／标准差原子序数、平均原子质量、平均共价半径、平均外层电子数。周期表数值来自RDKit。</p><p>带隙案例另外保留晶格位点元素；热导率保留温度值和温度类别。室温文字不强行换成某个精确K值。当前化学式解析器支持显式元素与数量序列，遇到括号或未支持的复杂写法需要先规范化。</p>
<h2>单类与组合特征比较</h2><p>通过<code>feature_groups</code>分别指定组成、材料描述符或实验条件。引擎为每组输入训练默认模型，再比较全部输入组合。互信息Top-K属于训练内选择，特征数与参数由内层验证决定。</p><p>混凝土仅配方ET开发MAE为8.489 MPa，加入龄期后为3.729 MPa。这个对照说明该数据中条件字段的价值；不意味着所有材料加入更多字段都会改善。</p>
''')
page('models','模型引擎','数据与建模','通用回归、二分类与纳米晶双路模型的执行方式。',['amadeus/engine.py','amadeus/tabular.py','allis_delivery/core.py','PIPELINE.md'],'''
<h2>通用回归流程</h2><ol><li>核对目标、特征、编号和分组，提取有标签训练记录。</li><li>在训练折内进行数值中位数填补、标准化与类别One-hot编码。</li><li>比较Dummy、Ridge、RF、ET、XGBoost和LightGBM。</li><li>对各特征组及组合输入做外层五折验证；分组数量不足时折数相应减少。</li><li>可选启用四种树模型的Top-K与Optuna TPE优化。</li><li>按开发指标选择配置，用全部训练数据拟合并预测候选，保存模型与运行文件。</li></ol><p>四个公开表格案例均比较三类输入×六种默认模型，加四种优化设置，共22组。自定义任务的设置数随特征组数量和优化开关变化。</p>
<h2>搜索预算与目标</h2><p><code>optimize=true</code>开启优化；<code>search_trials</code>设置每项搜索的目标试验数，案例为4。内层最多三折，搜索包含特征数量及模型参数。搜索存入SQLite，同一运行可恢复已完成试验。</p><p><code>selection_metric=mae</code>按误差选择；<code>regret</code>按预算1、3、5的筛选差距选择。默认配置不一定输给优化配置：混凝土与钢合金的已完成小预算比较都选中了默认组合ET。</p>
<h2>纳米晶：成对ET与直接评分ET</h2><p>成对ET学习两个历史实验点的相对发光差。预测候选时，针对历史参照预测差值，加回参照实测响应并聚合，得到40个用量点的曲线。取最高4点均值得到预测Q。</p><p>直接评分ET从配体表示直接预测Q。两个分支各自转换为名次，再按50%/50%平均名次排序。融合的是名次，不是不同尺度的预测分数。同分规则与评价中的随机平局期望见<a href="wiki:validation">验证与指标</a>。</p>
<h2>二分类入口</h2><p>二分类由<code>tabular.py</code>执行，比较ExtraTreesClassifier、逻辑回归、HistGradientBoostingClassifier与DummyClassifier。按平衡准确率选择，候选按指定正类概率排序。当前使用最多三折分组或分层验证，不使用通用回归的22组嵌套搜索。五个公开案例均为回归或排序任务。</p>
<h2>保存的分析结果</h2><p>回归运行保存配置、划分、逐折分数、折外预测、选中特征、搜索记录、候选预测及<code>model.joblib</code>。模型保存后会重载并核对预测一致性。<a href="wiki:architecture">系统架构</a>说明这些文件如何关联到项目。</p>
''')
page('validation','验证设计与指标','数据与建模','区分开发比较、留出评价、筛选效果和工程复核。',['results/reference/REPORT.md','docs/ENGINE_UPGRADE_RESULTS.md','results/unprepared-20261029/README.md','amadeus/engine.py'],'''
<h2>训练、开发与候选</h2><p>训练内部交叉验证用于比较模型与选择参数；留出候选用于评价最终预测。相同组成或配方的相关记录应归到同组。预处理和特征选择在训练管线内拟合，候选标签不进入模型输入。</p><p>公开案例的候选划分由准备脚本完成。自定义上传时，用户需要检查历史表与候选表的身份关系；引擎的内部GroupKFold不能自动补足所有科研场景的外部划分设计。</p>
<h2>误差与解释</h2><table><thead><tr><th>指标</th><th>含义</th><th>如何看</th></tr></thead><tbody><tr><td>MAE</td><td>预测与参考值绝对差的平均</td><td>越低越好，保留目标单位</td></tr><tr><td>R²</td><td>相对常数均值预测的拟合表现</td><td>结合分布与大误差样本一起看</td></tr><tr><td>平衡准确率</td><td>各类别召回率的平均</td><td>用于二分类模型比较</td></tr></tbody></table><p>开发集最佳CV分数已经参与模型选择，不能当作额外独立测试结果。热导率的MAE并不突出最大误差，因此案例同时报告高值SiC的低估。</p>
<h2>筛选指标Q与AUR</h2><p>纳米晶Q为每条40点曲线中最高4点相对发光FOM的均值。AUR为推荐预算1—5下，候选池最佳Q与已选最佳Q的平均差距，越低越好。B1/B3/B5分别描述对应推荐数量下找到的最好Q。</p><p>指标降幅表示筛选差距缩小，不是发光增幅。15个固定候选池来自90个配体的3套五折分配，配体在池间重复出现。最终报告按回顾性比较解释，保留每池及各预算结果。</p>
<h2>平局与可复算性</h2><p>名次构建采用平均名次处理相同分数。展示名单按固定规则打破平局；离线评价对并列组的随机选择计算精确期望，因此一次展示轨迹不必等于表格中的期望值。复算需使用同样的池、预算与平局规则。</p>
<h2>工程检查解决什么问题</h2><p>数值复算、保存重载、数据版本、候选标签隔离及快照一致性检查验证程序是否按设计执行。它们不能代替新增湿实验；公开带隙标签来自物理计算，也不称为本项目实际测量。</p>
''')
page('architecture','系统架构与状态','系统与开发','前端、Agent、数据工具和模型进程如何共同完成一次分析。',['amadeus/server.py','amadeus/workflow.py','amadeus/engine.py','amadeus/provider.py','amadeus/web/demo-adapter.js'],'''
<h2>模块关系</h2><div class="pipeline"><div>工作台界面<br><small>workbench.js</small></div><div>HTTP服务与项目状态<br><small>server.py · workflow.py</small></div><div>数据工具 / 模型引擎 / API<br><small>data_engine · engine · provider</small></div><div>预测、报告与项目档案<br><small>JSON · SQLite · joblib</small></div></div><p>前端按钮与对话工具修改同一份项目。模型结果来自执行模块，界面从保存的分析中读取；操作结果也返回给对话助手。</p>
<h2>Agent如何编排工具</h2><p>DeepSeek接收当前任务、字段、候选编号和已有选择，提出结构化工具调用。<code>converse</code>将工具名映射到实际函数，执行后将结果反馈给模型。一次对话最多12轮工具循环，重复的工具名与相同参数会复用本轮记录，避免重复执行。</p><p>资料搜索通过Search/Fetch；正文提取形成草稿；接受草稿后形成实验表；训练调用本机引擎。SciencePal参与方法研发，其研究档案放在<a href="wiki:history">项目记录</a>，不是运行时依赖。</p>
<h2>项目与数据版本</h2><p>SQLite数据库位于<code>outputs/amadeus-workspace/projects.sqlite3</code>。项目包含任务、数据集、字段映射、分析历史、计划、测量、消息、来源和操作回执。数据版本保留处理前后的表与处理原因，计划和测量关联当时的分析。</p><p>前端读取的可见项目只包含数据表预览和摘要；完整数据保留在本机项目中。导出项目JSON包含更完整的研究记录，分享前应检查自己导入的内容。</p>
<h2>执行与恢复</h2><p>HTTP动作启动后台线程；表格训练在子进程中执行，进度写入运行目录。页面轮询项目状态。取消请求设置停止标志，项目保存已经完成的内容。服务启动时将遗留的运行中状态标为interrupted，避免页面一直等待。</p><p>同一个<code>operation_id</code>用于去重操作回执；长任务完成后再发下一项动作。搜索恢复适用于相同数据和配置的运行，不能把旧试验直接当成新数据评价。</p>
<h2>在线版的适配</h2><p><code>demo-adapter.js</code>在浏览器内提供案例数据和动作回放，使用冻结预测与公开答案，项目存入浏览器存储。静态站不调用本机Python或DeepSeek。两端共用前端展示，运行能力由所在环境决定。</p>
''')
page('api','HTTP接口与Agent工具','系统与开发','本机项目接口、异步动作和服务适配位置。',['amadeus/server.py','amadeus/workflow.py','amadeus/provider.py'],'''
<h2>本机HTTP入口</h2><p>默认地址为<code>http://127.0.0.1:8787</code>。以下为当前内部接口，适合本机集成和开发调试。</p><table><thead><tr><th>请求</th><th>用途</th></tr></thead><tbody><tr><td>GET /api/config</td><td>本机标识与API是否已配置，不返回密钥</td></tr><tr><td>GET /api/projects</td><td>列出项目摘要</td></tr><tr><td>POST /api/projects</td><td>创建项目，接收title、goal</td></tr><tr><td>GET /api/projects/{id}</td><td>读取可见项目和操作状态</td></tr><tr><td>POST /api/projects/{id}/action</td><td>提交异步动作，返回202</td></tr><tr><td>POST /api/projects/{id}/cancel</td><td>请求停止</td></tr><tr><td>GET /api/projects/{id}/report</td><td>HTML报告</td></tr><tr><td>GET /api/projects/{id}/csv</td><td>计划CSV</td></tr><tr><td>GET /api/projects/{id}/export</td><td>项目JSON</td></tr></tbody></table>
<h2>动作请求示例</h2><p>先创建项目，从返回值取得真实id，再将它替换到请求路径。以下动作读取公开混凝土快照，不训练模型。</p><pre><code>{
  "action": "material_example",
  "operation_id": "my-unique-operation-001",
  "args": {"example": "concrete", "replay": true}
}</code></pre><p>收到202表示动作已接受。继续读取项目，检查<code>operation.status</code>是否为complete或failed，并读取message。不要把HTTP请求接受当作模型已完成。</p>
<h2>常用动作名称</h2><table><thead><tr><th>动作</th><th>作用</th></tr></thead><tbody><tr><td>chat / task</td><td>对话／设置研究任务</td></tr><tr><td>upload / extract / accept_extraction / process</td><td>导入、提取、接受草稿与数据处理</td></tr><tr><td>specialist / material_example / train</td><td>专用预测、公开案例与表格建模</td></tr><tr><td>adjust / save_plan / record / history_results</td><td>调整候选、保存计划、记录或揭晓结果</td></tr><tr><td>next_round</td><td>进入下一轮</td></tr></tbody></table><p>动作参数由<code>workflow.start</code>分发到实际函数。Agent工具使用另一组函数名，例如<code>train_table</code>、<code>extract_experiments</code>和<code>record_results</code>；不要把工具名直接替换成HTTP动作名。</p>
<h2>DeepSeek适配</h2><p><code>provider.py</code>当前调用<code>/chat/completions</code>、<code>/v1/tools/search</code>和<code>/v1/tools/fetch</code>。Search每次请求5项结果，query截取128字符。服务适配器对部分超时、限流和服务端错误最多尝试3次。接口是否可用取决于配置地址和账号服务权限；更换服务时修改适配层与相应测试。</p>
''')
page('cases','案例手册','研究案例','五种材料任务共用工作台，分别查看数据、模型和评价口径。',['amadeus/web/research-cases.json','docs/NEW_RESEARCH_CASES.md'],'''
<h2>选择案例</h2><table><thead><tr><th>案例</th><th>输入 → 目标</th><th>适合了解</th></tr></thead><tbody><tr><td><a href="wiki:nanocrystals">纳米晶配体</a></td><td>分子结构与用量 → 相对发光</td><td>双路预测、融合排序和响应曲线</td></tr><tr><td><a href="wiki:concrete">混凝土</a></td><td>配方与龄期 → 抗压强度</td><td>条件特征、模型比较和数据闭环</td></tr><tr><td><a href="wiki:steels">钢合金</a></td><td>元素组成 → 屈服强度</td><td>组成解析和材料描述符</td></tr><tr><td><a href="wiki:bandgap">双钙钛矿</a></td><td>组成与位点 → 计算带隙</td><td>计算标签与组成组隔离</td></tr><tr><td><a href="wiki:thermal">热导率</a></td><td>组成与温度 → 实验热导率</td><td>长尾误差与排序效果的区别</td></tr></tbody></table>
<h2>共同操作路径</h2><p>从首页点击“选择这个研究”，阅读数据与模型分析，检查候选名单，再保存计划、查看参考结果和生成报告。四个表格案例提供预填内容及逐步提示；纳米晶提供自动流程展示。</p>
<h2>如何理解已有结果</h2><p>本机首页选择案例时也可复用已有快照，便于快速体验。重新训练在本机引擎中主动发起。纳米晶是反复使用公开档案的回顾性研究，四个表格案例有各自固定留出划分。它们不共享一个可横向比较的“准确率”。</p>
''')
page('nanocrystals','纳米晶发光配体','研究案例','利用分子结构与用量响应比较候选配体。',['PIPELINE.md','results/reference/REPORT.md','allis_delivery/core.py'],'''
<h2>问题与数据</h2><p>在固定CsPbBr₃后处理场景中，根据历史配体的用量响应预测候选优先级。作者公开档案含4,447条反应记录，分出样品、空白与参照后，使用90种具有完整40点响应曲线的配体。</p><p>FOM为相对发光响应，Q为最高4点FOM均值。这里没有把相对发光直接换成绝对PLQY。用量来自原液浓度和加入体积，显示单位与内部模型单位需对应。</p>
<h2>方法与划分</h2><p>每个固定池使用36种历史配体与18种候选；共3套五折的15池，池间身份重叠。输入为原42维描述符与2048维Morgan计数指纹。成对ET产生曲线评分，直接ET产生Q评分，再平均名次。</p>
<h2>当前结果</h2><table><thead><tr><th>策略</th><th>AUR ↓</th><th>推荐3个的期望最好Q ↑</th></tr></thead><tbody><tr><td>随机</td><td>0.444518</td><td>1.484686</td></tr><tr><td>成对RF</td><td>0.293812</td><td>1.655376</td></tr><tr><td>成对ET</td><td>0.093398</td><td>1.860129</td></tr><tr><td>直接ET</td><td>0.109520</td><td>1.842430</td></tr><tr><td>等权排名融合</td><td>0.081803</td><td>1.853399</td></tr></tbody></table><p>融合相对成对ET的平均筛选差距降低12.41%，前三次最好Q略低约0.36%。相对RF的变化还包含表示和估计器差异，不能全部归因于融合。</p>
<h2>体验与复算</h2><p>在首页选择纳米晶案例，查看两路预测、融合排名与用量曲线，完成计划后再揭晓参考测量。默认第一池提供保存的权重；其他候选池可以回放已有预测。</p><pre><code># 从封存预测复算统一指标
./run_project.sh

# 重新训练一个池的两个ET组件
./run_project.sh models run --mode retrain --splits r0_f0 --output outputs/component_check</code></pre><p>第二条会实际训练。完整多池命令、预算和评价文件见仓库PIPELINE.md。</p>
''')
page('concrete','混凝土抗压强度','研究案例','用配方与养护龄期跑通通用回归分析。',['docs/ENGINE_UPGRADE_RESULTS.md','results/engine-upgrade/verification.json','amadeus/examples/concrete/provenance.json'],'''
<h2>数据与输入</h2><p>UCI Concrete Compressive Strength包含1,030条公开历史测量，作者I-Cheng Yeh，DOI 10.24432/C5PK67。输入为水泥、矿渣、粉煤灰、水、减水剂、粗骨料、细骨料及养护龄期，目标为MPa抗压强度。</p><p>按配方组成分组，同配方不同龄期一起保留。859条训练，171条留出候选；分组表示组成身份，不是有记录的实验批次。</p>
<h2>特征与模型比较</h2><table><thead><tr><th>输入</th><th>最佳默认模型</th><th>开发五折MAE / MPa</th></tr></thead><tbody><tr><td>配方组成</td><td>ET</td><td>8.489</td></tr><tr><td>养护龄期</td><td>RF</td><td>10.089</td></tr><tr><td>配方 + 龄期</td><td>ET</td><td>3.729</td></tr></tbody></table><p>22组设置中，优化配置未超过默认组合ET。最终模型的171条留出MAE为5.195 MPa。前3推荐的最好历史实测为79.297 MPa，候选池最好为79.986 MPa。</p>
<h2>完整工作流</h2><p>选择研究后，页面加载训练表、候选表和已有分析。按提示保存计划、揭晓历史结果，回填3条后进入第二轮；真实验收曾使用862条记录重训，并完成保存重开和报告生成。</p>
<h2>重跑与文件</h2><pre><code>PYTHONPATH=. .venv-allis/bin/python scripts/verify_engine_workflow.py
PYTHONPATH=. .venv-allis/bin/python scripts/run_material_benchmark.py</code></pre><p>上述命令会执行实际流程或模型比较。已有结果在<code>results/engine-upgrade/</code>；原始文件、标准表与字段说明在<code>amadeus/examples/concrete/</code>。交互图表及完整证据可在<a href="site:evidence.html#case">技术证据页</a>查看。</p>
''')
page('steels','钢合金屈服强度','研究案例','从化学组成构造特征，筛选高屈服强度候选。',['docs/STEELS_CASE.md','results/steels-case/verification.json','scripts/prepare_steels.py'],'''
<h2>数据与任务</h2><p>使用Matbench v0.1的matbench_steels，312种组成与实验屈服强度。只使用化学组成，不把抗拉强度、延伸率等其他实测性能输入模型。该数据没有热处理等工艺字段，因此本例分析组成与强度的关系。</p>
<h2>表示与划分</h2><p>14种元素比例加7项周期表统计描述符。规范化组成共312组，固定seed 42留出47种候选，265种用于训练。此为项目自定义划分，不是Matbench官方排行榜分数。</p>
<h2>结果</h2><p>元素比例ET开发MAE为81.88 MPa，仅描述符ET为108.76 MPa，组合ET为80.84 MPa。小预算优化未超过默认组合ET。</p><p>47种候选留出MAE为85.28 MPa，R²为0.832。前三种不同组成的历史屈服强度为2411.5、2402.3、1730.2 MPa，包含候选池最高值。</p>
<h2>操作与复算</h2><p>首页选择钢合金研究，检查元素特征和模型比较，保存名单后查看历史实测。已有结果进入下一轮会排除已记录项。</p><pre><code># 从附带数据重建特征与划分
.venv-allis/bin/python scripts/prepare_steels.py

# 执行建模和项目闭环
PYTHONPATH=. .venv-allis/bin/python scripts/verify_steels_workflow.py</code></pre><p>重建脚本会更新示例数据文件；重新评价产生的新结果应与已提交的固定版本区分。已有运行文件在<code>results/steels-case/</code>。</p>
''')
page('bandgap','双钙钛矿带隙','研究案例','在新组成上预测GLLB-SC计算带隙。',['docs/NEW_RESEARCH_CASES.md','results/unprepared-20261029/README.md','results/unprepared-20261029/independent_checks.json'],'''
<h2>数据来源与标签</h2><p>使用matminer公开的double_perovskites_gap。1,306条记录的目标来自GLLB-SC电子结构计算。界面和报告将其标为“计算参考值”，不是本项目或原始实验的光学测量。</p>
<h2>输入与评价</h2><p>保留元素比例、周期表统计及A/B位点元素。按规范化组成分组，训练1,111条（1,033个组成组），候选195条（183组）。同组成不跨训练与候选，模型依据训练内五折结果选择。</p>
<h2>当前结果</h2><p>选中组合特征ET，开发MAE约0.236 eV，留出MAE为0.210661 eV，R²为0.963036。训练中位数常数参考的留出MAE为1.271 eV。前三个推荐都落入候选池参考带隙的前10%。</p><p>本例目标是筛选高带隙候选。具体应用是否需要更高带隙、某个目标区间或其他性质约束，应在新的研究任务中另行定义。</p>
<h2>查看结果</h2><p>首页选择双钙钛矿研究，查看模型与候选，保存计划后揭晓计算参考值。文件在<code>results/unprepared-20261029/double_perovskites_gap/</code>，包括来源审计、封存预测、划分、模型比较与报告。</p><p>该案例是在四个满足规模和组成条件的数据集中预先抽取的两项之一，复用既有引擎。准备与执行脚本为<code>scripts/verify_unprepared_cases.py</code>，运行前应阅读脚本对已有评价的保护和本地原始文件依赖。</p>
''')
page('thermal','材料热导率','研究案例','结合材料组成与温度，分别检查数值预测和高值筛选。',['docs/NEW_RESEARCH_CASES.md','results/unprepared-20261029/README.md','results/unprepared-20261029/independent_checks.json'],'''
<h2>数据与条件整理</h2><p>使用matminer的citrine_thermal_conductivity公开实验数据。原始872条，按组成与条件整理后762条；同一组成与相同条件的重复项取标签中位数并保留原始值。642条用于训练，120条为候选，对应211和38个组成组。</p><p>明确记录的K温度作为数值；room temperature和standard保留为类别，不推断精确温度。目标单位为W/(m·K)。候选单位是组成与条件，可能有同材料不同温度。</p>
<h2>模型与结果</h2><p>沿用22组比较，选中元素比例及温度输入的XGBoost。留出MAE为7.713917 W/(m·K)，R²为0.268334；常数参考MAE为10.625 W/(m·K)。前三个推荐中2个位于候选前10%，前5包含池内最高值。</p>
<h2>读结果时注意高值误差</h2><p>室温SiC参考值372 W/(m·K)，预测约44.2，排名第4。排序找到高值候选与数值准确是两个问题。本例可用于观察高值筛选，也清楚展示仅用组成和有限条件预测绝对热导率的不足。</p>
<h2>操作和档案</h2><p>首页选择热导率研究，查看数据条件、模型分析和候选，再揭晓历史实测。记录结果时同时保留温度信息，不把同组成不同条件混为一个测量。</p><p>全部结果在<code>results/unprepared-20261029/citrine_thermal_conductivity/</code>，最差误差样本与数值复算在父目录的<code>independent_checks.json</code>。</p>
''')
page('development','开发、测试与部署','系统与开发','定位模块，增加数据或模型，并部署工作台和文档。',['amadeus/engine.py','amadeus/workflow.py','.github/workflows/pages.yml','tests/test_data_engine.py','tests/test_material_snapshots.py'],'''
<h2>目录结构</h2><pre><code>amadeus/
  server.py          HTTP服务与固定案例推断
  workflow.py        项目、动作、Agent工具与导出
  data_engine.py     提取、审计、转换与结构特征
  engine.py          回归模型比较与搜索
  tabular.py         CSV入口与二分类
  provider.py        对话、Search、Fetch适配
  examples/          标准案例数据、映射与来源
  web/               工作台、案例快照与生成的Wiki
allis_delivery/      纳米晶双路模型
allis_benchmark/     统一基线与指标评价
results/             已完成运行的公开结果
scripts/             数据准备、核验和页面构建
docs/wiki/           Wiki源文章与样式
tests/               单元与工作流检查</code></pre>
<h2>接入新数据集</h2><ol><li>将来源、许可、字段单位和样本身份写入数据说明。</li><li>准备历史表、候选表与mapping，先使用现有上传入口完成分析。</li><li>需要组成特征时参考现有准备脚本，不假定任意化学式都已被通用界面解析。</li><li>检查组隔离、候选标签、保存重开及导出。</li><li>需要成为内置案例时，再更新examples、research-cases元数据与快照构建脚本。</li></ol>
<h2>增加模型或Agent工具</h2><p>回归模型在<code>engine.py</code>的估计器创建和比较列表中注册，新增搜索参数应放入内层优化。保存统一的scores、candidates、order等字段，保证前端继续读取。</p><p>新增Agent工具需要在TOOLS定义参数，在函数分发映射中接到实现，并确认状态与导出。新增HTTP动作还需要在<code>workflow.start</code>中接入；工具schema不会自动创建HTTP路由。</p>
<h2>必要测试</h2><pre><code>.venv-allis/bin/python -m unittest discover -s tests -p test_data_engine.py
.venv-allis/bin/python -m unittest discover -s tests -p test_material_snapshots.py
node tests/test_demo_adapter.cjs
python3 scripts/check_wiki.py</code></pre><p>快照测试检查冻结结果接线，不重新训练；数据引擎测试模拟提取响应，不消耗API。真正的模型重训与完整工作流命令在各案例页单独说明。</p>
<h2>构建文档与在线部署</h2><pre><code>python3 scripts/build_wiki.py
python3 scripts/check_wiki.py</code></pre><p>Wiki由标准库Python构建，文章源在<code>docs/wiki/content.py</code>。生成独立HTML、搜索索引与站点地图，更新前端哈希清单。GitHub Actions在main分支相关路径变化后校验资产并发布Pages；在线站点只包含静态资源。</p><p>演示在网站根目录，文档位于<code>/wiki/</code>，研发证据页位于<code>/evidence.html</code>。工作台、证据页与Wiki互相链接。</p>
''')
page('faq','常见问题与排查','开始使用','解释运行差异、数据错误和结果保存。',['amadeus/provider.py','amadeus/data_engine.py','amadeus/engine.py','amadeus/workflow.py'],'''
<h2>在线为什么不能训练自己的数据？</h2><p>GitHub Pages只提供静态文件。在线端用已有预测体验操作；自己的CSV建模、文献提取和联网对话使用<a href="wiki:quickstart">本机版本</a>。</p>
<h2>没有API Key能做什么？</h2><p>可以浏览Wiki和在线案例；本机的数据表操作、固定模型推断与模型训练不依赖大模型API。自由对话、联网检索和基于大模型的正文提取需要配置接口。</p>
<h2>模型标识或搜索接口报错</h2><p>检查<code>.env.local</code>中的base URL和模型是否在账号可用范围内。当前模板模型名来自项目配置，不保证所有账号均有权限。若对话可用而Search/Fetch报错，需核对这两个路径是否被服务端支持；适配位置在provider.py。</p>
<h2>字段不一致、编号重复或目标无效</h2><p>历史表与候选表必须包含全部输入特征；目标、编号和分组不要选为输入。候选ID不能为空或重复。回归目标需为有限数，表格至少有10条有标签历史记录。按组验证需要至少两个可区分的组。</p>
<h2>PDF提取不到记录</h2><p>确认PDF有可复制文本。扫描页先做OCR；正文需要包含可归属于同一实验的材料、条件和测量值。提取字段缺少匹配的原文证据时会被省略，检查返回的issues和草稿。</p>
<h2>进度停止或重启后显示中断</h2><p>先读取操作message。重启会将遗留running状态标为interrupted，项目数据仍保留。相同配置的优化可用原运行ID恢复搜索；修改数据后应建立新的运行。启动端口被占用时用<code>--port 8788</code>。</p>
<h2>为什么看起来误差低，但某个候选差很多？</h2><p>MAE是整体平均，不描述每个候选。长尾材料性能尤其需要看最大误差和散点图。筛选排名与绝对预测也应分别评价，参见<a href="wiki:thermal">热导率案例</a>。</p>
<h2>记录存在哪里？</h2><p>本机项目在<code>outputs/amadeus-workspace/</code>；在线记录在浏览器存储。两者不自动同步。重要研究请导出项目和报告，本机备份前先停止写入并保存整个工作目录中的相关数据。</p>
''')
page('history','研发历程与方法取舍','项目记录','记录影响当前产品的研究选择与实现阶段。',['docs/evidence/research-records.md','docs/evidence/research-excerpts.md','docs/evidence/sciencepal-results.md'],'''
<h2>从科学问题与公开数据开始</h2><p>2026年10月19日起，从纳米晶生长、配体发光与材料主动学习相近研究出发，核查公开数据是否支持可评分任务。将测量点与独立材料分开，区分相对发光与PLQY，并优先检查完整条件的强基线。</p>
<h2>收敛到纳米晶双路模型</h2><p>整曲线Ridge未在保留配体上重现开发收益，部分配位特征在RF上有提升但没有稳定超过强通用表示。随后保留Morgan与成对ET，测试直接Q预测和固定等权名次融合。</p><p>融合改善平均筛选差距，同时保留前三次推荐的微小取舍。对数用量与用量差分原型没有成为当前性能来源。完整正负结果及原报告节选见<a href="site:evidence.html#journey">研发证据页</a>。</p>
<h2>SciencePal方法研究</h2><p>SciencePal使用自带研究流程完成问题与数据核查，之后在只提供数据、问题和规则的条件下提出并运行Direct RF、Curve RF和Ridge，并尝试组合。五池研究中直接评分RF优于该次探索组合，结果经本机另一份评价实现复算。</p><p>该工作作为方法比较与研发依据，未替换Amadeus现有生产组件。团队与Codex完成模型实验、工程实现、核查与产品交付。</p>
<h2>工程交付阶段</h2><p>10月28日统一训练、预测和评价入口，建立本机工作台与在线回放。10月29日接通通用数据和模型引擎，加入混凝土、钢合金、带隙和热导率案例，并统一预填与逐步引导。10月30日整理技术证据页与正式Wiki。</p><p>研究档案的日期与Git提交日期各自保留；未把拟合次数、聊天量或提交次数换算为人工工时。</p>
''')
page('resources','资源、贡献与维护','项目记录','查找第三方资源、团队分工和文档维护方式。',['THIRD_PARTY.md','requirements-allis.txt','docs/evidence/research-records.md'],'''
<h2>第三方资源</h2><p>数据、原论文和上游代码保留出处。Python环境版本在<code>requirements-allis.txt</code>，模型库包括scikit-learn、XGBoost与LightGBM，特征处理使用RDKit，参数搜索使用Optuna。</p><p>公开数据各自遵循来源许可，代码库许可不能自动代替数据许可。完整来源与使用说明以仓库THIRD_PARTY.md和各案例provenance／audit文件为准。</p>
<h2>团队协作</h2><p>材料方向成员负责科学问题、文献、字段与指标的专业核对。AI4Science方向成员共同完成数据、建模、Agent编排、界面和测试，其中一位主要负责架构与集成，另一位重点协作数据处理、联调和可视化。项目说明、演示与视频由团队共同交付。</p><p>SciencePal和Codex参与研发辅助。团队负责需求、方案取舍、材料判断、结果审阅和最终交付。</p>
<h2>修改文档</h2><p>各文章由<code>docs/wiki/content.py</code>中的页面定义维护。更新行为说明时同时核对所列代码文件；修改数字时附上运行结果来源。构建器生成本页目录、上一篇／下一篇、全文搜索和sitemap，避免手动维护多份导航。</p><p>发现问题可以在GitHub仓库提交Issue，附上所在页面、复现步骤、预期行为及相关公开日志。不要在Issue中粘贴密钥或私人实验数据。</p>
<h2>网站入口</h2><ul><li><a href="site:">产品演示</a>：体验五个研究案例。</li><li><a href="wiki:">项目Wiki</a>：使用、模型、接口与开发文档。</li><li><a href="site:evidence.html">研发与技术证据</a>：成果、运行档案与研究历程概览。</li><li><a href="https://github.com/nighty35628/ligand-screening">代码仓库</a>：源文件、配置、结果与版本历史。</li></ul>
''')

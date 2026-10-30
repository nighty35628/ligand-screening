# 界面语言与外观

`amadeus/web/preferences.js` 管理中文／English、深浅外观与偏好保存。控件位于全局页头右侧；报告无页头时置于正文上方。主题首次跟随系统，手动设置后使用保存值。

`en.json` 保存英文文案，`source-zh.json` 为源码与文档中提取的中文目录，`extra-zh.json` 补充五个案例各界面的动态文本。`amadeus/web/locale-en.js` 是浏览器使用的生成文件。英文文案在开发阶段借助项目已有的 DeepSeek 接口整理，随代码发布，使用时不调用翻译服务。

```bash
# 根据已有英文目录生成浏览器语言包，不请求 API
.venv-allis/bin/python scripts/build_locale.py
# 翻译新增文案，需要本机已有的 DeepSeek 配置
.venv-allis/bin/python scripts/build_locale.py --translate
# 更新 Wiki 页面与站点资源校验值
python3 scripts/build_wiki.py
```

显示层保留原始文案以支持切回中文；输入框、代码片段与原始项目数据保持原值。内置演示的预设输入可用英文展示，模型调用仍使用原有流程。本机对话请求携带界面语言，Agent 据此选择回复语言。

语言与主题分别存于 `amadeus-language`、`amadeus-theme`，与研究项目分开保存。切换不会训练模型或改写预测、候选 ID、测量值和原始数据。导出报告沿用界面设置，打印使用浅色页面。

浏览器验收脚本为 `scripts/check_preferences.cjs`，需要 Playwright 与 Chrome。检查包括五案例页面、语言往返、刷新与跨页面偏好、英文 Wiki 搜索、打印样式、移动视口和预测／任务状态一致性；不训练模型。已有开发环境可直接运行：

```bash
node scripts/check_preferences.cjs verify
```

# Wiki 页面检查

日期：2026-10-30。

- 19篇文档、104个可搜索章节、21个sitemap网址。
- 914处本地页面链接、锚点及资源引用通过检查；代码引用对应仓库实际文件；资产哈希一致。
- 本机Handler测试覆盖Wiki首页、嵌套页面、静态资源、目录跳转与不存在的路径，3项测试通过。
- 1440px桌面与390px手机实际Chrome渲染检查通过，无页面横向溢出、无JavaScript异常。
- 完成搜索章节跳转、键盘关闭、代码复制、移动目录导航检查。补充搜索框Enter打开首项及明确的Escape关闭行为。
- 四个表格案例的已有演示回放检查通过；没有运行新训练。

复查命令：

```bash
python3 scripts/check_wiki.py
python3 -m unittest discover -s tests -p test_wiki_routes.py
node --check amadeus/web/wiki/wiki.js
node tests/test_demo_adapter.cjs
```

本机服务需要项目Python依赖；纯文档构建和链接检查仅需Python标准库。

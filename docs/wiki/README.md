# Amadeus Wiki

源文章：`content.py`。每篇包含slug、标题、栏目、描述、代码来源和HTML正文。正文中的`wiki:models`指向Wiki内页，`site:evidence.html`指向站点根目录下的证据页。构建时转换成相对链接，因此本机与GitHub Pages共用页面。

```bash
python3 scripts/build_wiki.py
python3 scripts/check_wiki.py
```

只使用Python标准库。构建生成19个独立页面、章节搜索索引、sitemap和前端资产哈希。无需安装静态站点框架，也不调用训练或外部API。

前端支持分组目录、当前章节、移动目录、全文章节搜索、键盘操作、代码复制和上一篇/下一篇。搜索在浏览器内运行，查询不上传服务器。

本机由`amadeus.server`提供`/wiki/`；Pages发布`amadeus/web/`完整目录。新增页面时在content.py登记，其余导航、搜索与站点地图自动生成。

校验覆盖内链与锚点、源码引用、搜索路径、sitemap及资产哈希。本机HTTP路由检查位于`tests/test_wiki_routes.py`。

# 夏猫的博客

本站使用 Hexo、Shoka 和 GitHub Pages。文章位于 `source/_posts/`。本地预览和 CI 使用同一个构建入口。

## 本地开发

使用 Node.js 22 和 Python 3.12。在仓库根目录运行：

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r tools/requirements.txt
npm ci
npm run server
```

浏览器打开 <http://127.0.0.1:4000>。`server` 首次启动时构建站点，并在修改文章和配置后重新生成。单次构建用 `npm run build`，直接查看已有的 `public/` 用 `npm run preview`。

## 历史文章和发布

部分线上文章的 Markdown 已不在 `master`。构建会从固定的 `gh-pages` 提交恢复已发布的文章、资源和主题修复，再渲染新增或修改过的源码，最后生成分页、响应式图片和本地全文索引。第一次构建如果缺少历史 Git 对象，会从 `origin` 获取。要更新只有发布稿的文章，可以按原路由对应的 slug 在 `source/_posts/` 中补回 Markdown，保留原发布日期和永久链接。

推送到 `master` 后，Pages 工作流先构建、检查历史路由，再更新 `gh-pages`。PR 只构建。若有人直接修改了发布分支，先把该修改纳入构建基线。手动触发同一工作流可运行 `npm run deploy`。

## 图片

正文使用 WebP 阅读图，点击可以打开原图。首次构建会编码图片，后续构建复用 `.cache/shoka-post-images/`。首页首张壁纸直接出现在 HTML 中，后续图片在接近切换时加载；开启减少动态效果时只显示第一张。

主题壁纸的响应式版本随仓库提交，正常构建无需下载壁纸库。需要更新壁纸时，用本地壁纸原图目录和优化前的渲染目录运行 `python3 tools/wallpaper_assets.py <原图目录> <渲染目录>`。原始壁纸库和使用的修订号记录在该脚本的文件头。

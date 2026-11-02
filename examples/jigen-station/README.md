# 次元站 · JIGEN STATION

沉浸式二次元社区概念官网，包含海边站台、屋顶放映与画室三个滚动场景、活动收藏和入站证。

- `source/`：可编辑源码与必要素材。`source/` 保存可编辑 HTML/CSS/JavaScript 与最终使用的响应式场景图。未被最终页面引用的旧样式与旧素材没有收入示例。
- `site/`：已构建的静态成品，可直接放到静态托管服务。
- `build.mjs`、`package.json`、`package-lock.json`：可移植构建入口与锁定依赖。

## 本地预览

在仓库根目录运行（需要 Python 3）：

```sh
python3 -m http.server 8000 --bind 127.0.0.1 --directory examples/jigen-station/site
```

打开 <http://127.0.0.1:8000>。预览其他示例时，先停止当前服务器或换一个端口。请通过 HTTP 预览，避免直接双击 HTML 触发模块和资源加载限制。

## 编辑与重建

需要 Node.js 22.18+ 和 npm。在仓库根目录运行：

```sh
cd examples/jigen-station
npm ci
npm run build
npm run preview
```

修改 `source/` 后重新执行 `npm run build`。构建会重建 `site/`，直接修改 `site/` 的内容会被覆盖。构建使用 rolldown 1.2.15 与 lightningcss 1.33.0。

构建与原项目最终静态成品逐文件比对一致，保留原有页面、动画与交互。

## 静态演示范围

活动收藏和入站证仅保存到当前浏览器的 localStorage；没有账户系统、真实社区、报名接口或服务端数据。

素材与第三方许可见 [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md)。

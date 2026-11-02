# Pawly · 宠物健康观察

紫色主题的宠物健康概念官网，包含跟随指针转头的 Three.js 猫咪、症状填写、多步观察记录与文本下载。

- `source/`：可编辑源码与必要素材。`source/index.html`、`source/style.css`、`source/app.js` 和 `source/cat-scene.js` 是可编辑源码；`source/assets/` 保存最终使用的模型、海报图与素材许可说明。
- `site/`：已构建的静态成品，可直接放到静态托管服务。
- `build.mjs`、`package.json`、`package-lock.json`：可移植构建入口与锁定依赖。

## 本地预览

在仓库根目录运行（需要 Python 3）：

```sh
python3 -m http.server 8000 --bind 127.0.0.1 --directory examples/pawly/site
```

打开 <http://127.0.0.1:8000>。预览其他示例时，先停止当前服务器或换一个端口。请通过 HTTP 预览，避免直接双击 HTML 触发模块和资源加载限制。

## 编辑与重建

需要 Node.js 22.18+ 和 npm。在仓库根目录运行：

```sh
cd examples/pawly
npm ci
npm run build
npm run preview
```

修改 `source/` 后重新执行 `npm run build`。构建会重建 `site/`，直接修改 `site/` 的内容会被覆盖。Three.js 0.187.0；构建使用 rolldown 1.2.16 与 lightningcss 1.33.0。

构建与原项目最终静态成品逐文件比对一致，保留原有页面、动画与交互。

## 静态演示范围

问诊流程使用本地规则演示，输入留在本页内存中，可下载观察记录；没有真实 AI、兽医问诊、账户或服务端存储。

素材与第三方许可见 [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md)。猫咪模型与 Three.js 的原有许可说明同时保留在 `source/assets/third-party-licenses.txt` 和构建产物中。

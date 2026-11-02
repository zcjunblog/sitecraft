# 蓬蓬俱乐部 · FLUFF CLUB

蓝黄配色的宠物洗护概念官网，包含猫犬服务切换、响应式导航、常见问题和预约弹窗。

- `source/`：可编辑源码与必要素材。原项目的 `dist/` 本身就是未压缩、可编辑的原生 HTML/CSS/JavaScript，现整理为 `source/`；没有把压缩 bundle 冒充原始源码。
- `site/`：已构建的静态成品，可直接放到静态托管服务。
- `build.mjs`、`package.json`、`package-lock.json`：可移植构建入口与锁定依赖。

## 本地预览

在仓库根目录运行（需要 Python 3）：

```sh
python3 -m http.server 8000 --bind 127.0.0.1 --directory examples/fluff-club/site
```

打开 <http://127.0.0.1:8000>。预览其他示例时，先停止当前服务器或换一个端口。请通过 HTTP 预览，避免直接双击 HTML 触发模块和资源加载限制。

## 编辑与重建

需要 Node.js 22.18+ 和 npm。在仓库根目录运行：

```sh
cd examples/fluff-club
npm ci
npm run build
npm run preview
```

修改 `source/` 后重新执行 `npm run build`。构建会重建 `site/`，直接修改 `site/` 的内容会被覆盖。没有第三方运行或构建依赖；构建仅使用 Node.js 内置文件 API，将 `source/` 原样复制到 `site/`。

构建与原项目最终静态成品逐文件比对一致，保留原有页面、动画与交互。

## 静态演示范围

预约表单只在浏览器中展示确认状态，不会发送到门店，也没有真实预约、短信通知或后台管理。

素材与第三方许可见 [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md)。

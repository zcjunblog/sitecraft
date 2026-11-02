# 静态网页发布：体积、图片、首页速度与部署包

对标已经完成的制作过程：既保留设计与交互，也完成素材瘦身、静态构建、缓存配置、实际加载检查和可直接部署的交付。不是只交一张漂亮截图或一个源码目录。

## 1. 先确定预算与发布目录

分清四个量：最终 ZIP/tar 文件大小、部署文件解压总量、首屏实际请求与传输量、再次访问的传输量。它们不能互相替代。

按页面类型先选预算；已有项目记录优化前后的同口径值。下面是本技能的**评审起点**，不是所有站点的硬限制：

| 类型 | 可采用的起点 | 调整原则 |
| --- | --- | --- |
| 简约导航/工具首页 | 首屏 HTML/CSS/JS 的压缩正文合计尽量不超过 100 KiB；避免框架运行时和远程字体 | 不把所有图标、收藏数据、设置面板预加载 |
| 普通单页品牌官网 | 部署归档约 3 MiB 内；主要单张位图约 150–350 KiB；首屏实际传输约 1 MiB 内 | 根据图片数量、显示尺寸与细节要求调整，保持画质 |
| 作品集、视频或 3D 页面 | 按首屏、后续画面和可选体验分别定预算 | 不能把全部视频、原图或 3D 依赖算成必须立即加载 |

检查器默认以归档 3072 KiB、单图 350 KiB 提醒复核，可通过参数调整；超出不自动证明设计不合格，也不能不加解释地忽略。记录单位，1 KiB=1024 B，不混用估算口径。

## 2. 图片必须实际优化并保留证据

- 原始生图与高分辨率素材保留在源码/素材目录，发布目录只包含使用的衍生图。按实际显示宽度和必要 DPR 缩放；需要时提供 srcset/sizes，手机另做裁切。
- 照片优先比较 WebP/AVIF 与合适质量的 JPEG；有透明、动画、线稿或兼容性要求时保留合适格式。不能仅改扩展名，也不能把所有 PNG 无差别转成有损照片格式。
- 每张主要位图记录原文件、输出文件、尺寸、字节、处理决定与画质复核。比较前后实际文件，检查毛发、边缘、细字、透明与色彩；不追求压缩率而损坏细节。
- 已经小且合适的图可不再有损压缩，记录 preserve 及理由；优化后变大也需说明原因。没有原图或记录时标注未核实，不根据扩展名声称“已压缩”。
- 首屏关键图不要 lazy-load；非首屏按需加载并预留宽高/比例。`loading="lazy"` 是浏览器启发式策略，近屏图片仍可能提前请求，必须看实际瀑布图。
- SVG 适用于 Logo、线性图标等；保留必要的 SVG/PNG/ICO/Apple 图标兼容版本，不拿横版 Logo 直接缩成看不清的标签页站标。

图片记录 JSON 放在 QA/构建资料中，不放进网站公开根目录：

```json
{
  "images": [
    {
      "output": "assets/hero.webp",
      "source": "../source-assets/hero-original.png",
      "decision": "resize-and-reencode",
      "quality_review": "passed"
    },
    {
      "output": "assets/brand.png",
      "source": "../source-assets/brand.png",
      "decision": "preserve",
      "reason": "已是小尺寸透明品牌图，继续有损压缩无收益",
      "quality_review": "passed"
    }
  ]
}
```

`source` 相对图片记录文件解析，也接受绝对路径。质量复核是人工记录，不是脚本计算出的画质分数。

## 3. 构建保持轻量与原有行为

- 构建工具可以有开发依赖，线上仍保持纯静态。沿用已有可靠构建器做标准 JS/CSS 压缩；不以正则删除代码，不靠重度混淆、反调试或增加运行库实现“压缩”。
- 根据脚本依赖安排 defer、async、模块分割与合并；不能盲目拼接 ES 模块或改变执行顺序。可选语录、设置面板等延迟加载，不阻塞主任务。
- CSS/JS 与适合长期缓存的资源采用内容指纹或可靠版本地址，引用保持同步。资源内容变更必须有新地址，不能给同名会变化的文件盲配一年 immutable。
- 远程字体、CDN 库、第三方统计与站标服务都要有明确必要性和回退；不把首屏建立在不稳定的外部请求上。
- Three.js、模型、视频和较重动效按位置与使用时机加载，提供静态画面/WebGL 不可用回退；需要 HTTP 访问的模块不能承诺双击 file:// 一定可用。
- 保存构建压缩前后记录。Gzip/Brotli 估算只说明潜在文本压缩收益；线上是否启用需读实际 Content-Encoding。不要给已经压缩的图片重复生成无意义的编码副本。

## 4. 对最终部署包运行文件检查

先完成优化和构建，再生成归档；归档后代码变了就重新生成并复查。检查器只读，不修改文件或自动转换图片：

```sh
python3 /path/to/sitecraft/scripts/audit_static.py release/site \
  --archive release/site.zip \
  --image-log qa/image-optimization.json \
  --report qa/package-audit.json --strict
```

ZIP/tar 内站点根目录若为 `dist/`，加 `--archive-prefix dist`。使用平台官方打包器时保留它所需的 hosting 元数据，不能为适配检查器私改已签名/待保存的归档。

报告包含：归档体积与 SHA-256、解压文件总量、图片占比、最大十个文件、逐文件字节与本地 Gzip 估算、图片尺寸及来源对比、HTML/CSS 显式资源引用、外部引用、归档与最终目录的逐文件内容比对。

- `fail`：缺入口、资源缺失、格式后缀不符、归档内容不一致、不安全路径、私密文件/依赖/测试误入等，修复后重查。
- `needs_review`：体积超预算、缺优化或画质记录、未检查归档、归档里有未知额外文件等。未知额外文件会使 content_matches=false；清理、补证据、优化或说明合理例外，不当作全绿。
- 默认遇错误退出 1；`--strict` 遇待复核退出 2。成功采集或进程退出 0 不代表速度合格。
- 检查器不执行 JS，也不自动证明所有运行时 import/fetch 路径有效；用浏览器验证。文件头只能提供格式/部分尺寸信息，不替代浏览器解码与看图。

包内不应含 node_modules、Git、测试、QA、原始大图、私密备份、密钥或无用 source map。部署说明与 QA 报告可随交付提供，但与公开 web root 分开。确认入口层级、相对路径、MIME 和必要文件齐全。

**从最终归档解压到全新临时目录，用 HTTP 服务打开后复验**图片、主要操作、手机画面与控制台，而不只运行可编辑源码。归档检查器不会提取文件；临时预览使用已检查的安全归档和合适工具。不要在生产来源导入测试收藏或覆盖用户设置。

## 5. 实测首页，不用包体积代替速度

优先复用项目现有性能工具。附带脚本需 Node、已有 Playwright 与可用 Chromium；通过 `--playwright-module` 指定已有模块，必要时用 `--channel chrome` 复用本机 Chrome。它不安装依赖，也不自动修改网站。

```sh
node /path/to/sitecraft/scripts/measure_page.mjs \
  --url http://127.0.0.1:8080/ --expect-title "实际网站名称" \
  --profile mobile --runs 3 --warm \
  --playwright-module /project/node_modules/playwright \
  --report qa/mobile-performance.json
```

桌面另跑 `--profile desktop`。手机默认 390×844、DPR 1、4 倍 CPU 减速、150ms 延迟、1600/750 十进制 kbps 的传输限速；这些只是可复现的实验设置，不等于某款真机或真实 4G。可用参数调整，报告保留实际设置及生效的 CDP 方法；无法生效会报错。

至少记录冷访问 3 次的中位值与最慢值，并比较热访问。脚本为每个冷样本使用独立上下文并禁用缓存；热访问先单独预热再导航。Service Worker 被阻止，因此不代表离线缓存体验；需要该能力时另验。测量停留时间可调，不滚动整页，报告中 LCP/CLS 是此窗口内的观测值。

查看：TTFB、FCP、观测到的 LCP、CLS、首屏请求与 CDP 实际传输数据、最大资源、错误请求、控制台错误及响应头。确认测到的是目标站点，不是登录门、错误页或占位页。检查首屏图与近屏 lazy 图片是否争抢带宽，是否为了动效下载了不必要的重包。

报告分别记录未处理的 JS 异常和 console.error。传输进行中或被取消时累积已观测正文，不把它当成 0 B；此时 transferred_bytes_complete=false，总量是当前观测下界，应查看 request_issues 而不是声称所有资源已完整加载。

以 LCP≤2.5s、CLS≤0.1 作为常用体验参考并结合目标环境评审；真实用户 INP 的良好参考为≤200ms。**这个加载脚本不测 INP，不生成 Lighthouse 分数，少量实验也不等于真实用户 p75 Core Web Vitals 合格。**没有数据填未测，不填 0。可用工具不足时记录限制、完成能执行的检查，不伪造速度结论。

## 6. 已授权上线后复核

只做本地部署包时，提供待应用的配置与待验收项；不把配置文件写好了视为服务器已生效。已获部署授权时，在正常发布流程中复核：

- 域名、HTTPS、主域与 www 跳转、页面/静态资源状态码与 MIME；不存在的 JS 应返回正确缺失状态，不错误地回退为首页 HTML。
- HTML 与需要及时更新的缓存脚本可使用 no-cache 进行重新验证；no-cache 不等于禁止缓存。带指纹资源可长缓存，其余资源按更新方式定期限。
- 实际请求是否返回 Gzip/Brotli Content-Encoding、Cache-Control、ETag/Last-Modified；适用时验证条件请求的 304。Nginx 不会自动读取静态平台的 `_headers` 文件，按实际托管方式配置并保留已有必要响应头。
- 先上传新指纹资源再换 HTML，保留旧资源过渡；有上一版完整包可回退。配置、发布与权限沿用当前任务已有授权，不另造例行审批。
- 在线上环境重复目标页面测速。localhost、一次 curl、文件下载耗时、压缩比，都不能单独证明所有地区用户“秒开”。

## 7. 交付附简洁验收单

报告与部署包同版，至少列出：

| 项目 | 必填信息 |
| --- | --- |
| 部署包 | 文件名、字节/KiB、SHA-256、解压体积、文件数、部署根目录 |
| 图片 | 优化前后字节与尺寸、保留原因、画质复核结果 |
| 构建 | JS/CSS 标准压缩、版本化与延迟策略，必要的 Gzip/Brotli估算 |
| 首屏 | 环境、冷/热样本、FCP/LCP/CLS 观测、传输量、重资源和待处理项 |
| 线上配置 | 压缩、缓存、HTTPS/域名、实际是否验证；本地未测就标待验收 |
| 使用说明 | 上传哪一层、是否需要构建或 HTTP 预览、更新与回退方式 |

审计报告和速度日志的状态要保留。不要把“已测量”改写成“已达标”，不要只交一句“已优化”。

## 制作过程参照与来源

- jkhcz.com 的历史优化记录：首屏两张图约 3.3 MB→309 KB，部署包约 19.4 MB→1.96 MB；转换合适 WebP、非首屏延迟、检查画质、保留源 PNG，并保留 Three.js 和无 WebGL 回退。该记录当时明确未做线上服务器测速。
- nav.gs 的制作记录：原生静态运行、开发期标准压缩、脚本约 85,947 B→68,657 B，构建 Gzip 约 21,277 B；内容指纹、独立延迟脚本、站标缓存及可直接上传的发布包。线上又检查了真实传输、缓存响应头、304、域名与资源一致性。

上面的数字属于历史版本，不当作当前线上成绩或所有项目的硬限制；对标其优化动作与证据链，不照搬品牌视觉。

技术依据：[Web Vitals](https://web.dev/articles/vitals)、[HTTP Cache-Control](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Cache-Control)、[DevTools Network](https://chromedevtools.github.io/devtools-protocol/tot/Network/)、[Playwright](https://playwright.dev/docs/api/class-browsertype)。

维护检查器时，运行 `python3 -B -m unittest discover -s /path/to/sitecraft/tests -p 'test_*.py'`，以及设置 `PLAYWRIGHT_MODULE` 为已有 Playwright 模块路径后运行 `node --test /path/to/sitecraft/tests/measure_page.test.mjs`。未设置模块时浏览器测试会跳过，跳过不算通过。

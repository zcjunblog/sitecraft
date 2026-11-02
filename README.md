<p align="center">
  <img src="docs/images/sitecraft-banner.svg" alt="Sitecraft — 一句需求，交付完整静态官网" width="100%">
</p>
<p align="center">
  <a href="https://github.com/zcjunblog/sitecraft/releases/latest"><img alt="Release" src="https://img.shields.io/github/v/release/zcjunblog/sitecraft?style=flat-square&color=6d55e8"></a>
  <img alt="Codex Skill" src="https://img.shields.io/badge/Codex-Skill-20202a?style=flat-square">
  <img alt="HTML CSS JavaScript" src="https://img.shields.io/badge/HTML_%C2%B7_CSS_%C2%B7_JS-Static-20202a?style=flat-square">
  <a href="LICENSE"><img alt="Code license: MIT" src="https://img.shields.io/badge/Code-MIT-20202a?style=flat-square"></a>
</p>
<p align="center">面向静态官网的设计与交付 Skill。<br>从真实视觉参考出发，把构图、素材、动效、交互和轻量部署一起做好。</p>
<p align="center">
  <a href="#产出示例">产出示例</a> ·
  <a href="#安装">安装</a> ·
  <a href="#一句话开始">使用</a> ·
  <a href="skills/sitecraft/SKILL.md">技能规范</a> ·
  <a href="#历史作品参考">历史作品</a>
</p>

## 产出示例

四个可运行示例，包含可编辑源码、静态成品、构建脚本与独立说明。截图均来自实际运行的网页；点击图片可查看大图。

<table>
<tr>
<td width="50%" valign="top">
<a href="docs/images/pawly.webp"><img src="docs/images/pawly.webp" alt="Pawly 宠物 AI 问诊官网，紫色 3D 猫咪与症状输入入口" width="100%"></a>
<h3>Pawly · 宠物 AI 问诊</h3>
<p>真实 WebGL 猫咪、独立头部跟随鼠标、动态光照、点头互动。问诊流程在本机整理信息，可下载观察摘要。</p>
<p><a href="examples/pawly">查看源码与运行说明 →</a></p>
</td>
<td width="50%" valign="top">
<a href="docs/images/fluff-club.webp"><img src="docs/images/fluff-club.webp" alt="蓬蓬俱乐部宠物洗美官网，钴蓝底与黄色浴缸中的小狗" width="100%"></a>
<h3>蓬蓬俱乐部 · 宠物洗美</h3>
<p>钴蓝与明黄、轻松的门店气氛。服务浏览、预约预览，以及经过实际展开检查的选择控件。</p>
<p><a href="examples/fluff-club">查看源码与运行说明 →</a></p>
</td>
</tr>
<tr>
<td width="50%" valign="top">
<a href="docs/images/jigen-station.webp"><img src="docs/images/jigen-station.webp" alt="次元站官网，黄昏海边站台的沉浸式二次元场景" width="100%"></a>
<h3>次元站 · 二次元聚集地</h3>
<p>海边站台、屋顶放映与画室构成连续观看体验。章节、光影和页面操作共同参与场景。</p>
<p><a href="examples/jigen-station">查看源码与运行说明 →</a></p>
</td>
<td width="50%" valign="top">
<a href="docs/images/zhijian-florist.webp"><img src="docs/images/zhijian-florist.webp" alt="枝间花店官网，白底黑色大标题与自然红玫瑰花束" width="100%"></a>
<h3>枝间 · 鲜花零售</h3>
<p>纯白底、放大的中文排字与自然红玫瑰。花束选择、送花建议和本机花单形成完整浏览路径。</p>
<p><a href="examples/zhijian-florist">查看源码与运行说明 →</a></p>
</td>
</tr>
</table>

> 这些页面经过不同版本的迭代和反馈，并非全部由当前版本一次生成。Pawly 是静态问诊流程演示，未连接真实 AI 或兽医；其余示例的预约、社区、价格与订单也属于演示设定。具体边界见各自 README。

## 安装

需要 Git 和 Python 3.9+，在终端运行：

```sh
git clone https://github.com/zcjunblog/sitecraft.git
python3 sitecraft/tools/install.py
```

默认安装到 `~/.codex/skills/sitecraft`；设置了 `CODEX_HOME` 时安装到其 `skills/` 目录。安装器仅复制 Skill，已有版本会备份到技能目录之外，不会把示例、截图展示页和开发依赖一起装入。安装后在下一轮对话中调用。

也可以在 Codex 中直接说：

```text
请从 https://github.com/zcjunblog/sitecraft 安装 skills/sitecraft 这个 Skill。
```

[下载独立 Skill 压缩包](https://github.com/zcjunblog/sitecraft/releases/latest/download/sitecraft.zip) · [查看安装器](tools/install.py)

## 一句话开始

```text
$sitecraft 做一个宠物 AI 问诊官网，首页放一只 3D 猫咪，头部平滑跟随鼠标。
```

```text
用 Sitecraft 做一家鲜花零售门店官网，明亮、简约、大气。
```

```text
做一个企业官网，突出真实产品和制造工艺，交付可直接上传的静态部署包。
```

自然语言可使用“Sitecraft”或“官网设计”，显式调用为 `$sitecraft`。出现“静态官网”“企业官网”“静态网页”“纯静态”“官网”时，技能会向宿主提供自动选择指引；具体是否加载仍由宿主与模型决定。

缺少名称、配色或栏目时，执行者根据主题作合理默认，完成制作和复查；已有品牌、明确参考及局部修改范围优先。

## 它怎样工作

| 环节 | 具体做什么 |
| --- | --- |
| 看实际参考 | 查看相关品牌画面和当前素材，分析主体尺度、图文关系、材质与阅读顺序。内置实图包含不同方向，也保留被否定的案例。 |
| 决定构图 | 从访问目的和内容确定表达。新建官网默认采用与主题相符的沉浸体验；配色、字体与密度随项目变化。必要时先比较少量真实首屏小样。 |
| 做完整交互 | 设计按钮、下拉、弹层与表单的实际状态，核对键盘、焦点与手机操作。默认不使用 Emoji 充当 UI 装饰。 |
| 分别做动态 | 场景 Motion、连续转场、动态光影各自承担作用；支持暂停、离屏处理和减少动态效果。 |
| 看画面再修订 | 查看桌面、手机和重要展开状态；将任务清晰度与视觉完成度分开评审，首次交付包含内部修订。 |
| 按部署包验收 | 检查图片处理、标准压缩、版本化资源、包体积及资源完整性，再从最终包预览和测量首页加载。 |

Skill 通过说明、参考图和可执行检查器指导制作。成品仍取决于模型、素材、浏览器能力和实际修订；当前案例不足以证明每个主题都能一次命中审美，也不以测试全绿替代视觉判断。

## 本地查看示例

无需先构建，仓库已经包含静态成品：

```sh
cd sitecraft
python3 -m http.server 8080 --directory examples/pawly/site
```

打开 `http://127.0.0.1:8080/`，将目录替换为下表路径即可切换项目：

| 示例 | 静态成品 | 可编辑源码 |
| --- | --- | --- |
| Pawly | [`examples/pawly/site`](examples/pawly/site) | [`source`](examples/pawly/source) |
| 蓬蓬俱乐部 | [`examples/fluff-club/site`](examples/fluff-club/site) | [`source`](examples/fluff-club/source) |
| 次元站 | [`examples/jigen-station/site`](examples/jigen-station/site) | [`source`](examples/jigen-station/source) |
| 枝间花店 | [`examples/zhijian-florist/site`](examples/zhijian-florist/site) | [`source`](examples/zhijian-florist/source) |

本地 HTTP 服务只负责提供文件，运行这些页面不需要 Node 后端或数据库。修改源码后，在对应示例目录执行 `npm ci && npm run build`；具体 Node 要求见各示例说明。正式部署上传 `site/` 的内容。

## 历史作品参考

下面两个网站是作者已有作品，为 Skill 提供制作经验与质量参照。此处展示截图和访问入口，不声称它们由当前 Skill 重新生成，也不包含这两个网站的源码。

<table>
<tr>
<td width="50%" valign="top">
<a href="https://nav.gs/"><img src="docs/images/nav-gs.webp" alt="nav.gs 几颗黑橙子简约导航" width="100%"></a>
<h3>nav.gs · 简约导航</h3>
<p>让搜索和常用入口直接成为页面主体。</p>
<p><a href="https://nav.gs/">访问网站 ↗</a></p>
</td>
<td width="50%" valign="top">
<a href="https://jkhcz.com/"><img src="docs/images/jkhcz.webp" alt="jkhcz.com 几颗黑橙子独立软件创作空间" width="100%"></a>
<h3>jkhcz.com · 几颗黑橙子</h3>
<p>角色、场景、排字与交互共同表达创作空间。</p>
<p><a href="https://jkhcz.com/">访问网站 ↗</a></p>
</td>
</tr>
</table>

截图采集于 2026-11-03；线上内容可能继续更新。[截图与素材来源](docs/asset-provenance.md)

## 仓库结构

```text
sitecraft/
├── skills/sitecraft/       技能入口、参考图、检查器与维护用例
├── examples/              四个示例的 source、site 和构建说明
├── docs/images/           README 实际网页截图
├── tools/                 安装、打包与仓库检查
├── THIRD_PARTY_NOTICES.md  第三方素材与许可边界
└── LICENSE                自有代码和文档的 MIT 许可
```

## 验证与贡献

```sh
python3 tools/check_repository.py
python3 -B -m unittest discover -s skills/sitecraft/tests -p 'test_*.py'
```

静态发布检查器与首页性能工具位于 [`skills/sitecraft/scripts`](skills/sitecraft/scripts)，完整操作见[静态发布规范](skills/sitecraft/references/static-release.md)。性能工具需要调用者已有的 Playwright 与浏览器，不会自动安装；本地测量不能当成线上速度。

欢迎提交带有**原始需求、实际截图、问题位置与修改后对照**的 Issue 或 PR。新增案例请说明适用条件和局限，不把某个品牌的颜色或字体固化为所有项目的答案。

## 许可

自有代码、脚本与文档采用 [MIT License](LICENSE)。第三方库、CC0 猫咪模型、品牌参考截图和示例图像按各自来源与说明处理；MIT 不授予第三方品牌资产的再利用权。详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 与[素材溯源](docs/asset-provenance.md)。

<p align="center">Created by <a href="https://github.com/zcjunblog">zcjunblog</a> · <a href="https://jkhcz.com/">几颗黑橙子</a></p>

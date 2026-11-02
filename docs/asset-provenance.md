# 素材溯源与公开范围

本次按本地素材记录、源码引用、优化记录与模型文件核验，未下载新素材，未读取环境变量文件或凭据。路径以仓库内预期结构表示；原工作目录中的 QA 并不全部作为公共源码分发。缺少生成调用原始回执时，以下明确区分“本地文字记录说明”和“逐图证据”。

## 四个示例

| 示例 | 实际素材与证据 | 确认范围与缺口 |
| --- | --- | --- |
| `examples/fluff-club` | 原 `asset-briefs.json` 明确写 Codex 内置 image_gen，列出 `hero.jpg`、`salon.jpg` 两条提示词；网页实际引用这两张图 | 可标为虚构品牌的原创 AI 生成演示素材；原目录只保留 JPG，没有高分辨率原图或独立生成回执 |
| `examples/jigen-station` | 原 `qa/image-generation-briefs.md` 记录内置 image_gen 的 station/studio/screening 三图提示词；`qa/image-optimization.json` 将 WebP 与相应原 PNG 对应 | 这三图及 station-small 有生成/处理记录。最终首页另引用 arrival/cinema/atelier 及移动裁切，`originals/immersive-arrival.png`、`immersive-cinema.png`、`immersive-atelier.png` 存在，但该 brief 和优化清单未覆盖这三张；当前逐图来源证据不完整 |
| `examples/zhijian-florist` | 原 `qa/assets-and-prompts.md` 写明内置 imagegen，覆盖 peach/white/pink/sunny；`qa/images.json` 与后续 `release-images.json` 记录裁切与 WebP 对应 | 早期四图有生图说明；最终页面还引用 roses-bouquet 及方形裁切，原目录存在 `roses.png`、`roses-bouquet.png`，现存提示词/处理清单未逐图覆盖，不能补写不存在的调用记录 |
| `examples/pawly` | 原 `originals/asset-sources-and-review.json`、`grab3d-LICENSE.txt`、`qa/model-processing.json`、`qa/image-optimization.json` 及运行时 `third-party-licenses.txt` 相互对应 | 已用的是 Grab3D 黑猫与其预览，CC0；不是 Polyfork 候选，也不是直接由 image_gen 生成的猫 |

所有示例用于展示静态 HTML/CSS/JS、响应式排版与本地交互。宠物洗护预约、动漫社群活动、花束价格/取送政策和评价文案不证明实际商家、真实交易或客户反馈。Pawly 的问诊整理在前端完成，未接真实 AI 或兽医，不把模型、图片或页面当作医疗认可。现有源码的这些边界应随复制和部署保留。

## 黑猫派生核验

对 `originals/grab3d-black-cat.glb` 与实际 `source/assets/cat.glb` 的只读比较确认：原二进制数据作为派生文件前缀逐字节保留；POSITION、NORMAL、TEXCOORD_0 访问器仍为原索引，材质、图片和纹理条目相同。派生仅增加索引等数据，拆分连通几何岛，增加 `HeadPivot` / `CatHead` 节点。原文件 `skins` 与 `animations` 均为 0，不能宣传原作者提供了 rig 或现成动画。

`source/assets/cat-poster.webp` 与原 `grab3d-preview.webp` 逐字节相同。运行时许可副本包含 Three.js MIT 全文与 Grab3D CC0/程序化生成披露，部署包应保留该文件。出处与许可链接见 [第三方说明](../THIRD_PARTY_NOTICES.md)。

## 技能参考图

外部品牌七张参考图有原站 URL、2026-11-03 采集日期与单帧验证记录；记录并不包含截图再分发授权。它们是设计分析参考，排除在仓库 MIT 授权之外；不能将品牌图像、海报、角色等搬进新生成站。完整映射见第三方说明与技能 `references/visual-benchmarks.md`。

花店前后版本六张截图来自本地演示站。三个 `rejected-*` 截图的本地 provenance 只记为“local generated prototype, user rejected”，没有逐元素来源审计。保留时应维持失败案例标签、来源和用途，不包装成外部客户案例，也不对截图内容作一揽子 MIT 声明。

## 发布包取舍

- 最终示例所需的本地图片、Grab3D 派生模型/预览和许可声明可随源码保留，缺少逐图记录的替换图片应继续补证据，不伪造许可结论。
- Polyfork 候选 GLB、候选预览及其下载网页缓存不是最终运行资源，建议不纳入公共包。它的本地授权记录与 CC0 不同。
- `node_modules`、原项目 `.git`、`.openai/hosting.json`、部署账户绑定记录、认证门页面截图 `flower-shop/qa/auth-gate.png` 和无关 QA/浏览器缓存不属于四例可复用源码；建议从发布包剔除。认证截图本次所见为通用登录门，未见个人身份数据，但不需要作为花店素材公开。
- 内置品牌截图若继续发布，应保留第三方来源和 MIT 排除说明；如果希望发布包仅包含许可证据明确的资产，可只保留原站链接。这是发布范围选择，不是本审阅替权利人作出的许可判断。

本审阅没有全量检查任何可能存在的隐藏配置或账号材料；敏感文件不应因“示例源码授权”而自动进入公共包。源码扫描未发现四例请求远程字体、远程图片或运行时 CDN 库；页面中的 AAHA 链接是信息来源链接，不是合作或背书。

## README 成品截图

2026-11-03 使用浏览器实际采集，统一请求视口1440×960，导出1425×950，逐张查看后转为WebP。截图不包含浏览器地址栏、账号面板或认证门。

| 文件 | 页面来源 | 展示范围 |
| --- | --- | --- |
| `docs/images/pawly.webp` | 本仓库 Pawly 最终静态成品 | 当前3D问诊示例 |
| `docs/images/fluff-club.webp` | 本仓库蓬蓬最终静态成品 | 宠物洗美示例 |
| `docs/images/jigen-station.webp` | 本仓库次元站最终静态成品 | 二次元场景示例 |
| `docs/images/zhijian-florist.webp` | 本仓库枝间最终静态成品 | 鲜花零售示例 |
| `docs/images/nav-gs.webp` | https://nav.gs/ | 作者历史作品；仅截图，不含源码 |
| `docs/images/jkhcz.webp` | https://jkhcz.com/ | 作者历史作品；仅截图，不含源码 |

历史作品截图展示当时页面，不代表两个线上项目由本版本Skill重新生成。网站可能继续更新；截图中的第三方站标仍归其权利人。

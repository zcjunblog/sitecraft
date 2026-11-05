# 第三方素材与许可说明

仓库根目录的 MIT 许可适用于维护者有权授权的技能文本、脚本及示例代码；第三方软件、模型、品牌截图与其中的商标/作品仍按各自来源和许可处理。此文件不为第三方资产重新授予 MIT 许可，也不表示有关品牌参与或认可本项目。

## 落地页版式数据

技能包的 `references/landing-patterns.json` 收录了 UI UX Pro Max 落地页目录中的版式名称、栏目顺序和操作位置，并转为 JSON。来源固定到 [上游提交与原始数据](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/ccce51cba388476d4f403091ddb91636d5cd9fed/src/ui-ux-pro-max/data/landing.csv)，随包保留 [Next Level Builder 的 MIT 许可原文](skills/sitecraft/references/landing-patterns-LICENSE.txt)。

## 示例图片

`fluff-club` 的宠物与店内图片、`jigen-station` 早期 station/studio/screening 插画、`zhijian-florist` 早期 peach/white/pink/sunny 花束有本地内置 image_gen / imagegen 的生成说明，属于为虚构演示项目制作的原创 AI 生成演示素材，不是真实门店、商品实拍、客户或医疗背书。后续替换图片的逐图证据缺口见 [素材溯源](docs/asset-provenance.md)，不能仅凭文件名把所有位图认定为同一次生成。

本说明记录生成来源，不额外承诺 AI 输出的独占权或第三方权利状态。示例中的价格、评价、活动、预约、购物袋和问诊流程属于静态演示；Pawly 未连接真实 AI、兽医或诊疗服务。

## Grab3D 黑猫模型与预览

使用位置：`examples/pawly/source/assets/cat.glb`、`cat-poster.webp` 及构建后的对应指纹文件。

- 来源：[Grab3D Black Cat](https://grab3d.com/models/animals/black-cat/)。
- 原许可：[Grab3D LICENSE.txt](https://grab3d.com/dl/black-cat/LICENSE.txt)，CC0 1.0 Universal；本地原件与示例运行时许可副本一致。
- 预览图直接沿用原包 WebP。模型由原包 GLB 派生，保留原始顶点属性、材质与内嵌纹理，以新增索引拆分头/身并增加 `HeadPivot`。原模型无骨骼、无动画；跟随鼠标和打招呼由示例代码实现。
- 原来源披露：Blender 脚本程序化生成，脚本获 AI 编程辅助；几何与纹理由程序生成，并非生图模型直接生成。

原包许可文字：

```text
CC0 1.0 Universal (CC0 1.0) Public Domain Dedication

To the extent possible under law, Grab3D has waived all copyright and related or neighboring rights to the
3D models, textures and images in this package. This work is published from: Germany.

https://creativecommons.org/publicdomain/zero/1.0/legalcode

Origin / AI disclosure
----------------------
Method: procedural (no AI-generated geometry or textures, AI-assisted code)
Built procedurally with Blender scripts. The scripts were written with the help of an AI coding assistant. No
generative AI model produced the geometry or textures directly.
If your platform asks whether AI was used in the creation process, note that the generator scripts were
written with an AI coding assistant.
```

## 第三方软件

| 软件 | 版本 | 用途 | 许可 |
| --- | --- | --- | --- |
| [Three.js](https://github.com/mrdoob/three.js) | 0.187.0 | Pawly 的 WebGL 与 GLTFLoader；随运行时构建分发 | MIT，完整声明见下方及示例 `source/assets/third-party-licenses.txt` |
| [rolldown](https://github.com/rolldown/rolldown) | 1.2.15 / 1.2.16 | 示例 JS 构建工具 | MIT；安装包保留其 LICENSE 与第三方声明 |
| [lightningcss](https://github.com/parcel-bundler/lightningcss) | 1.33.0 | 示例 CSS 构建工具 | MPL-2.0；安装包保留其 LICENSE |

构建工具由包管理器按锁文件安装，不把它们或 `node_modules` 重新许可为仓库 MIT。其他三个示例未发现随页面分发的外部运行库。CSS 字体名称是本机字体回退列表，未发现随四个示例打包的字体文件或远程字体请求。

Three.js 许可全文：

```text
Three.js

The MIT License

Copyright © 2010-2026 three.js authors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
```

## 设计参考截图

`skills/sitecraft/references/benchmarks/` 中的截图仅用于设计观察和教学分析，来源如下（本地记录采集日：2026-11-03）：

| 文件 | 来源 |
| --- | --- |
| `apple-desktop.webp`、`apple-mobile.webp` | [Apple Mac mini](https://www.apple.com.cn/mac-mini/) |
| `teenage-desktop.webp` | [teenage engineering](https://teenage.engineering/products) |
| `a24-desktop.webp` | [A24 Films](https://a24films.com/films) |
| `linear-desktop.webp`、`linear-mobile.webp` | [Linear](https://linear.app/) |
| `duolingo-desktop.webp` | [Duolingo](https://www.duolingo.com/) |

截图包含的品牌字标、产品、照片、角色、电影海报、界面与文案不属于本仓库的 MIT 授权。现存记录提供了来源和采集信息，未提供第三方截图再分发授权；“仅作参考”是使用目的说明，不等于取得许可。不得把这些内容当成示例站的自有素材或客户背书。若需要只含明确可重分发资产的精简包，可去掉这些截图并保留来源链接。

`skills/sitecraft/references/visual-cases/flower-*.webp` 来自维护者本地花店演示的前后版本；`rejected-book-full.webp`、`rejected-daily-tools.webp`、`rejected-book-sample.webp` 是本地生成原型的失败案例截图。它们仅作为案例证据，不代表客户认可；现存记录未逐项审计截图内所有元素，因此不能据此对图中每项素材统一授予第三方 MIT 许可。

## 未使用候选资产

原工作目录曾保存 [Polyfork Arched Black Cat](https://polyfork.dev/asset/arched-black-cat-407cf6) 作为候选。它没有用于最终示例；其本地来源记录写明独立再分发受限，不能按 Grab3D 的 CC0 处理。公共示例无需包含该候选 GLB、预览或网页缓存。

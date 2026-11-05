# 从真实参考到可执行设计资产

用于新站和整体重做。先观察参考，选择它能解决的设计关系，再用本项目内容实现。用户不用选择模板或填写下面的技术字段。

## 五种起点

数据与实际图片在 [design-assets.json](design-assets.json)，原创实现位于 [hero.css](../assets/hero.css)，工具为 [design_assets.py](../scripts/design_assets.py)。每例有六组关系：构图、中文排字、主体、光线材质、行动、手机编排；包含观察、用途、两端具体起点和代码位置。

| ID | 实际参考 | 借鉴的关系 | 使用条件 |
| --- | --- | --- | --- |
| object-focus | Apple Mac mini，桌面/手机历史截图 | 单件实物与中央阅读轴 | 单一产品图足以支撑视觉，先理解再行动 |
| scene-immersive | teenage engineering，桌面历史截图 | 场景尺度、结构与材质 | 大场景有清晰主体及文字空间；手机须重新取景 |
| work-surface | Linear，桌面/手机历史截图 | 用途标题与真实工作画面 | 有实际产品界面或明确标注的演示 |
| collection-led | A24 Films，桌面历史截图 | 类别、作品和动作直接构图 | 主要任务是挑选，有足够好的作品/商品图 |
| retail-object | 枝间，桌面/手机认可稿 | 商品体量与中文标题平衡 | 突出主推实物与品牌情绪，不用于高密度筛选 |

外部图来源与采集范围见 [visual-benchmarks.md](visual-benchmarks.md)。枝间是多轮反馈后的本地演示稿，见 [visual-cases.md](visual-cases.md)。不能把它当新找的外部商业案例，也不能声称它是当前版一次生成的结果。静态参考未提供任何原站动效验证。

**数值是原创实现起点，不是原站 DOM 测量，更不是所有品牌的审美标准。** 没有手机图的案例，其手机方案明确是 Sitecraft 改编。新项目仍需看实际手机渲染。

## 选择并落实

```sh
python3 /path/to/sitecraft/scripts/design_assets.py search --query '鲜花零售，顾客想直接选花'
```

匹配词只排序候选。实际打开相关图片，再按本项目主要任务、素材条件与气质选择。想直接挑多种花，优先考虑目录关系；想突出一束主推，可考虑商品关系；只有场景照片时，不能硬套透明实物构图。已有品牌与用户指定参考优先。

可以先导出设计计划，按现有项目直接实现：

```sh
python3 /path/to/sitecraft/scripts/design_assets.py plan \
  --case retail-object --brief '做一个花店品牌官网' --out qa/design-plan.json
```

也可以在**空目录**生成可改写的 HTML/CSS 首屏。参数必须使用本次实际内容；不要照抄这个例子的品牌与文案。

```sh
python3 /path/to/sitecraft/scripts/design_assets.py compose \
  --case retail-object --brief '做一个花店品牌官网' \
  --brand '本次品牌名' --headline '本次具体标题' \
  --body '本次品牌与服务说明。' --action '看看花单' \
  --target-copy '实际花单内容或明确的演示说明。' \
  --media materials/bouquet.webp --media-alt '本次实际花束的说明' \
  --media-origin '用户提供的商品图' --fit '主推花束承担品牌主体，访客先看花再挑选。' \
  --site release/site --out qa/design-plan.json
```

目录骨架可重复传入 `--media` 和对应的 `--media-alt`。工具只复制本地项目素材，不把参考截图装进网站。首屏目标区包含 `--target-copy` 的真实 DOM；执行者继续实现与按钮文案匹配的花单、联系或演示目标，不能靠一段泛化说明冒充可选购功能。

骨架输出实际中文 DOM、主图、手机规则和可到达的主要动作。它是设计起点，用户内容、图片形状、品牌字体与任务可以要求改变构图；不要求照着它成稿。骨架只有基础按钮反馈，不代表 Motion、连续转场或光影已完成，后续仍按现有动态流程实现与取证。

输出计划默认 `draft`。实际看过案例并落实下列内容后才改为 `ready`：

- `selection.fit`：为什么适合这次任务；`not_borrowing`：不搬用的品牌元素；`adaptations`：本次具体改编及原因。
- `content`：实际品牌、中文标题、说明、入口；`media` 逐项记录本地路径、替代文字和来源，图像必须已经可用。
- `relations[].target.desktop/mobile`：将起点改成当前标题、字体/字重/断行、主体尺度与焦点、光线、按钮位置、手机阅读顺序。`hook` 指向实际代码选择器或素材位置。
- `implementation.files`：实际使用的实现文件；仅借原理而自行实现时，填本项目的 CSS/设计文件，`kind` 改为 `project-original`。

纯排字或真实产品 DOM 自身足以成立时，可以用 `visual_mode:typography` 或 `product-dom`、空 `media` 和具体 `visual_note`，并链接项目原创实现。不为通过检查强塞图片；六组关系仍解释实际焦点、背景、层级和手机组织。

**不让骨架反过来限制案例选择。** 无匹配的内置案例时，按 [参考索引](design-library.md) 找真实作品，保存实际截图，然后 `plan --case custom` 建立空记录，填写真实来源、采集日期与范围、图片、观察和本项目实现文件。`custom` 没有内置样式要求。不能给内置案例改个 URL 后声称访问了新网站。离线且没有合适图时，如实保留缺口。

参考阶段的 `reference_notes` 仍保留来源与总判断，`reference_capture` 必须对应计划中一张实际图，新增 `design_plan` 指向这份计划。阶段工具绑定计划、参考图、实现文件和项目主图的哈希；修改后需要重新核对。第三方图仅用于分析，许可见 [asset-notices.md](asset-notices.md)。

## 从计划到实际截图

需要直接组成整站时，按 [整站组装与自动化](assembly-and-automation.md) 使用项目数据与原创组件；已有页面可自行实现。`doctor` 可复用现有环境，`prepare` 可从真实回执取路径，以下显式参数仍适用于已有环境。

首屏硬检查通过后，在 `visual` 阶段重新采集当前两端首屏：

```sh
python3 /path/to/sitecraft/scripts/workflow.py start --run qa/sitecraft --stage visual
python3 /path/to/sitecraft/scripts/workflow.py check --run qa/sitecraft \
  --tool browser --primary '.primary' --primary-target '#details' \
  --playwright-module /project/node_modules/playwright
```

使用上一步返回的**本次**报告路径生成对照。工具自动取参考阶段登记的计划，不另选有利参考：

```sh
python3 /path/to/sitecraft/scripts/workflow.py check --run qa/sitecraft \
  --tool comparison --browser-report qa/sitecraft/checks/ACTUAL_ID/review.json
```

输出 `comparison.json` 和同名自包含 HTML，展示两端参考、当前截图和六组关系。保留历史截图原始比例，不把不同尺寸并排说成相同视口像素对比。没有手机参考时，手机栏显示缺口，桌面原图仍在同一对照页可看。

工具只生成对照，**不会自动宣称视觉通过**。打开参考与当前图片，按真实尺寸检查中文和主体；再生成观察记录：

```sh
python3 /path/to/sitecraft/scripts/design_review.py template \
  --comparison qa/sitecraft/checks/ACTUAL_ID/comparison.json > qa/visual-review.json
```

每项填 `region`（实际画面位置）、`observation`（当前可见事实）、`reference_relation`（与参考/目标的关系）、`decision`（保留、调整或有理由改编），实际通过后才填 `pass`。两端均检查六组关系，共十二项。手机缺参考的部分明确按本项目改编目标判断，不编造原站观察。`mode:self` 是自审；只有真实的其他评审者才用 `independent`。

有效观察例如：“手机标题第二行只剩一字，花束上缘顶到按钮；与计划的完整语义断行和独立操作区不符。改标题段宽与媒体间距后重看。”只写“高级、符合要求、参考一致”不能支撑判断；脚本无法替代看图识别这种空话。

## 失败、修复与复看

发现问题时保留本轮对照和 `status:fail` 的观察记录，通过阶段 `record` 留下失败尝试。每个问题写入 `findings`，使用稳定 `id`；修复后保留该 ID，不从记录中删除。

```json
{
  "id": "mobile-heading-wrap",
  "profile": "mobile",
  "dimension": "typography",
  "problem": "标题末行只有一个字，与上方主图竞争焦点",
  "status": "resolved",
  "change": "调整标题段宽和中文语义断行",
  "before": "before/mobile.png",
  "after": "sitecraft/checks/NEW_ID/mobile.png",
  "recheck": "新手机图中标题两行完整，按钮未被挤出首屏"
}
```

路径相对于观察记录。`before` 留原截图，`after` 必须是本次实际采集的当前对应视口，两图不同。修复修改了网站时，沿现有版本约束从失效的首屏阶段复验，再重新 `start visual → browser → comparison → 观察 → record`。更换参考或合理改变设计目标时回到 references 阶段，不能事后缩减目标掩盖未修问题。

视觉阶段结果新增 `comparison`（清单）和 `visual_review`（观察记录）两个产物，`reference_transfer` 检查的 `evidence` 同时引用这两个名称。其余品牌气质、层级与手机检查保留。缺少对照、记录未验证、已记录问题未解决或截图/计划哈希变化，都不能登记通过。

证据齐全只表明有人按声明做了评审，不意味着“审美认证”或保证偏好命中。静态画面、动态过程、功能、性能仍分别验证。维护这轮先完成资产与检查机制，实际质量提升等统一生成评估后再报告。

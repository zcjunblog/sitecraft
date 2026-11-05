# 整站组装与检查自动化

工具由 AI 使用，用户继续用日常语言描述，不需要填 JSON 或选择技术栈。已有成品可直接局部修改，不强制重建。

## 原创整站资产

[完整可打开示例](../assets/example.html)、[项目数据例](../assets/example-spec.json)、[整站 CSS](../assets/site.css)、[控件 JS](../assets/site.js) 与 [组件生成器](../scripts/site_components.py) 可分别借用。示例链接到同目录 CSS/JS，直接打开即可，不需安装开发依赖。[几何示意](../assets/sample-object.svg) 是原创组件素材，不是商业摄影质量基准。

按信息关系组合四种区块：`collection` 用于挑商品/作品；`services` 直接展示服务差异；`story` 用于确有内容的说明；`contact` 提供实际联系方法或明确本地演示。不会自动插入客户数字、评价、资质、FAQ 或“三步走”。导航只指向已存在的目标，手机菜单与咨询弹层包含键盘退出、焦点返回和减少动态效果路径。

软件与工具类可参考 [无图片的真实 DOM 工作台例](../assets/example-workspace-spec.json)：`visual_mode:product-dom`、`media:[]`、`workspace.items` 提供可切换的实际演示内容。也可用 `workspace` 区块放在正文。标题与可操作产品共同构图，不能只把同一套纸色、抒情标题和小标签包在所有产品外面。纯排字方向可声明 `visual_mode:typography` 并说明实际焦点，不强塞图片。

把当前项目内容写入数据，再执行一次组装：

```sh
python3 /path/to/sitecraft/scripts/design_assets.py assemble \
  --spec qa/site-spec.json --site release/site --plan qa/design-plan.json
```

结构参照数据例，图片路径相对输入文件；每张图记录 `path/alt/origin`。`site.sections` 只含实际需要的区块，顺序由任务决定；`primary_target` 指向实际区块，例如 `#flowers`。`contact.demo:true` 仅预览留言，不发送请求、不保存信息；真实联系方式填入 `methods` 的 `label/href`。主题色、字体、图像与区块仍须按参考改编，不能把组装成功当作设计完成。

`compose --sections 项目区块.json` 也支持已有首屏参数。用户给定布局或当前品牌不适合内置起点时，自行实现并沿用验收。具体 Motion、连续转场和动态光影仍按主题实现与取证，菜单过渡不代表三项均完成。

## 一次定位环境

首屏入口写好后，执行以下命令。优先沿用当前项目或宿主已有环境，不安装软件、不下载浏览器、不改用户浏览器资料。

```sh
python3 /path/to/sitecraft/scripts/workflow.py doctor --run qa/sitecraft
```

探测当前项目近邻祖先目录、技能目录、现有 `PLAYWRIGHT_MODULE` 配置和已安装浏览器；不递归扫描任意旧任务目录。可用模块位于其他位置时，由执行者传一次 `--playwright-module /actual/path`，必要时加 `--channel chrome`。结果缓存进工作流。`available` 仅表示找到文件，实际启动与验收仍由报告证明。

组装器将唯一主动作标记为 `data-sitecraft-primary` 并指向真实页内目标，通常直接执行：

```sh
python3 /path/to/sitecraft/scripts/workflow.py check --run qa/sitecraft --tool browser
```

自有代码可加同样标记，或用 `doctor --primary '.actual-action' --primary-target '#actual-target'` 记录绑定。不按“第一个按钮”猜业务动作。工具缺失保留未验证和具体原因，不反复安装或读取源码试参数。

## 自动归集本轮证据

`start` 后记录实际观察，文件只须包含评审者与相应检查的状态、事实，例如：

```json
{"reviewer":"实际执行评审者","checks":{"background_and_fonts":{"status":"pass","detail":"本次实际观察到的主图、中文字体与背景关系"}}}
```

```sh
python3 /path/to/sitecraft/scripts/workflow.py prepare \
  --run qa/sitecraft --observations qa/observations.json
```

工具从本轮回执取报告、截图及关联路径，返回 `prepared.evidence`，传给现有 `record --evidence 实际路径` 即可。只有登记工具完成原有验证，阶段才算通过。`prepare` 不运行浏览器、不编造观察、不省略哈希检查。

必要的业务和人工材料用 `--artifact name=path` 补入：

| 阶段 | 需要补入 | 自动收集 |
| --- | --- | --- |
| brief | `brief` 需求计划 | 观察与阶段字段 |
| references | `design_plan` | 计划中实际参考图、来源/观察/改编摘要 |
| first-screen | 通常无额外项 | 实际入口、浏览器报告 |
| visual | 用视觉观察文件作 `--observations` | 当前两端截图、比较清单、从十二项观察归并的阶段检查 |
| site | `interaction_log` | 整页截图、浏览器报告、已采集的动态帧清单 |
| performance | 通常无额外项 | 本轮桌面/手机性能报告 |
| delivery | `package`、`handoff`、适用的图片复核 | 两次审计和独立解压预览报告 |

视觉阶段仍先采图、生成对照，再实际看图填写十二项。把 `visual-review.json` 直接传给 `prepare --observations`，不再另写四份阶段总结。归并只引用已有观察，不改变未验证状态，也不删除失败问题。

缺观察、原生报告、产物或浏览器环境时不能放行。旧观察不接受；旧报告与改变后的截图由回执和哈希校验拒绝。工具减少路径、摘要与字段整理，实际设计与复验继续执行。

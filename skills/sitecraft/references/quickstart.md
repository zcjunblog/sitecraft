# 新站快捷路径

此页供执行者使用。普通用户只需说需求。已有品牌和指定参考优先，局部修改沿原范围。

1. 看实际参考与项目素材，决定主动作、主体、排字和手机顺序。内置案例用 `design_assets.py search --query '当前任务'` 查；无匹配则选实际外部作品，使用 custom 计划。不要将所有行业都选为花店案例。
2. 有合适资产时优先用 [完整组合数据例](../assets/example-spec.json) 的结构准备当前 `qa/site-spec.json`，执行 `design_assets.py assemble --spec qa/site-spec.json --site release/site --plan qa/design-plan.json`，再按品牌改编。只用需要的区块。已有品牌、自有产品 DOM 或资产确实不适配时自行实现，写明具体差异；不为套模板抛弃实际内容。

   软件与工具优先考虑 [真实 DOM 工作台数据例](../assets/example-workspace-spec.json)，让可操作产品承担视觉；零售按挑选关系展示商品，服务按实际场景和流程组织。不要把换行业变成给同一套抒情包装换名字。已有明确 CI 或指定方向保持一致。
3. **先写可打开的实际首屏。七阶段约束验收顺序，不要求先填完全部记录才写网页。** 主图、中文与主要入口同时落盘。参考计划中的实现文件应已存在，不能登记未来才写的文件。
4. `workflow.py init --site release/site --out qa/sitecraft --request '原始需求'` 返回 `brief_template` 路径。补齐受众、标题、主要动作、内容、明确约束；按用户原话确认效果范围和预算。WebGL 必须明确选择；关闭 Motion/转场/光影时填用户明确要求的 `source_quote`。模板不代表需求已经通过。
5. 按 brief → references → first-screen → visual → site → performance → delivery 验收。每阶段 `start`，实际检查/观察，`prepare` 自动整理，再 `record`；失败修复复验，状态由工具判定。具体手工材料见 [归集表](assembly-and-automation.md)。

常用命令（路径以当前任务实际返回值为准）：

```sh
# 写好入口后定位已有环境，不安装软件
python3 /path/to/sitecraft/scripts/workflow.py doctor --run qa/sitecraft

# 每阶段先 start；组装器已标记唯一真实主动作
python3 /path/to/sitecraft/scripts/workflow.py check --run qa/sitecraft --tool browser

# 视觉阶段：本次 browser 报告 → 参考对照 → 实际看图填写观察
python3 /path/to/sitecraft/scripts/workflow.py check --run qa/sitecraft \
  --tool comparison --browser-report qa/sitecraft/checks/ACTUAL_ID/review.json
python3 /path/to/sitecraft/scripts/design_review.py template \
  --comparison qa/sitecraft/checks/ACTUAL_ID/comparison.json > qa/visual-review.json

# 用已填写的真实观察整理路径；视觉观察可直接归并
python3 /path/to/sitecraft/scripts/workflow.py prepare --run qa/sitecraft --observations qa/visual-review.json
# 将返回的 prepared.evidence 用于 record，不手写原生报告
```

`template --stage brief` 也输出需求文件结构。需要某阶段字段用 `template --stage 阶段`，参数用 `--help`；不需要为了猜 JSON 格式读取检查器源码。分阶段详细约束见 [workflow-contract.md](workflow-contract.md)，仅在当前阶段需要时查阅相应部分。实际动效、控件与图片优化按原规范验证，不以记录齐全或截图生成代替效果判断。

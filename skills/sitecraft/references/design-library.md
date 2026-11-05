# 找参考与可复用做法

先看用户提供的资料。新建与整体重做按 [可执行设计资产](executable-design-assets.md) 选择实际案例，并把观察转成两端设计计划和实现位置。内置五例是少量种子，不覆盖所有行业；无匹配时用下方来源找行业与访客任务相近的真实网站，建立 custom 计划。需要补操作或局部实现时再找辅助例。按 [从首屏到交付](delivery-workflow.md) 记录实际选择。只有网站名、标签命中或一段赞美不算参考阶段完成。

| 要解决的问题 | 从哪里找 |
| --- | --- |
| 信息顺序、首屏尺度、手机编排 | [Land-book](https://land-book.com/) 可按行业、区块和移动端找真实案例。[Minimal Gallery](https://minimal.gallery/) 适合看排版和留白。[Recent](https://recent.design/) 可找视觉与动效方向，Godly 的原地址目前跳转到这里。 |
| 单个组件怎么实现 | [Jiro](https://jiro.build/) 有预览、组件和模板。优先看实际状态和结构，需要复用源码时核对该条目的访问条件和授权。 |
| 字标与排字 | [Font In Logo](https://www.fontinlogo.com/) 用于研究字体搭配。实际使用要核对字体授权与中文字符覆盖。 |
| 展开、切换与退出 | [60fps](https://60fps.design/) 可查动效案例。记录触发、持续时间、打断时的行为和减少动态效果后的状态。 |
| 辅助立体图标 | [3dicons](https://3dicons.co/) 提供渲染图标。[开源 V1 仓库](https://github.com/realvjy/3dicons) 标注 CC0。其他条目逐项查许可。需要绕看主体时按 [3D 指南](web-3d.md) 验证实际几何。 |

## 借鉴开源工作流

- [Anthropic Frontend Design](https://github.com/anthropics/skills/tree/main/skills/frontend-design) 把明确的视觉主张放在实现前。[Impeccable Critique](https://github.com/pbakaus/impeccable/blob/main/skill/reference/critique.md) 检查设计能否对应到特定产品。Sitecraft 先记录主案例能解释的设计关系，再从桌面和手机实景评审气质和品牌特征。

- [UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) 将可检索的设计数据和规则输出成设计系统。[Brand Design MD](https://github.com/SpaceZephyr/brand-design-md) 将品牌语言写成明确的颜色、间距、字体和材质值。Sitecraft 用同样的结构记录当前项目的决定和来源。具体品牌的资产和规范按用户给定材料和相应授权使用。
- [Oil UI](https://github.com/oil-oil/oil-ui) 以并排截图比较方向。[Variate](https://github.com/Nutlope/variate) 用同一组件的不同设计探索局部问题。固定内容与操作，改变版式或主体关系，避免用颜色变化充当不同方案。
- [华书设计](https://github.com/alchaincyf/huashu-design) 将真实参考、风格样张和设计体检分开。[Frontend Slides](https://github.com/zarazhangrui/frontend-slides) 让人先看实际效果再谈风格。Sitecraft 采用实景对照和能验证的事实检查，并按建站范围控制备选数量。

这些来源按问题查阅。需要离线工作时用当前素材与内置基准。实际带进成品的外部代码、图标、字体和图片应记录来源与授权。

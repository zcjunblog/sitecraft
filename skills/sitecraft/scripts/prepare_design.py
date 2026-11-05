#!/usr/bin/env python3
"""Prepare optional information architecture notes; visual case selection is in design_assets.py."""

import argparse
import json
from pathlib import Path


CATALOG = Path(__file__).resolve().parents[1] / "references" / "landing-patterns.json"
PATTERNS_BY_INTENT = {
    "service": ("hero-features-cta", "minimal-single-column"),
    "product": ("product-demo-features", "feature-rich-showcase"),
    "portfolio": ("portfolio-grid", "minimal-single-column"),
    "immersive": ("immersive-interactive-experience", "scroll-triggered-storytelling"),
    "event": ("event-conference-landing", "hero-features-cta"),
}


def make_brief(intent, brief):
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    candidates = [catalog["patterns"][key] for key in PATTERNS_BY_INTENT[intent]]
    lines = [
        "# DESIGN",
        "",
        "## 原始需求",
        "",
        *("> " + line for line in brief.splitlines()),
        "",
        "## 版式候选",
        "",
        "先用 design_assets.py 选择并观察真实案例，形成 design-plan.json。以下候选只辅助安排信息，"
        "不能替代主视觉选型、中文排字、素材选择或参考到成品的对照。",
        "",
        "选择一项作为构图起点，再按真实业务内容调整栏目和主要入口。"
        "只有取舍会明显影响结果时，才渲染两个首屏。品牌规范和用户明确要求优先。",
    ]
    for item in candidates:
        lines.extend([
            "",
            f"- **{item['name']}**。{item['section_order']}",
            f"  原版式的操作位置为 {item['cta_placement']}。",
        ])
    lines.extend([
        "",
        "即时可用的主要入口始终可达。仅采用已有资料支持的栏目、数据与功能。"
        "这里的原始版式只提供结构参考。",
        "",
        f"[版式数据来源]({catalog['source']})",
        "",
        "## 项目决定",
        "",
        "- 访客、首屏要讲清的事、主要操作",
        "- 品牌资料与演示边界",
        "- 看过的参考与取舍、所选版式、手机重排",
        "- 字体、颜色、间距、素材及其来源",
        "- 主要交互的反馈、失败和回退状态",
        "",
        "## 验收证据",
        "",
        "- 桌面、手机和主要交互的截图或操作证据",
        "- 发现的问题与修订后复查",
        "- 资源和发布检查、未验证项",
    ])
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intent", required=True, choices=PATTERNS_BY_INTENT)
    parser.add_argument("--brief", required=True, help="Original user brief")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if not args.brief.strip():
        parser.error("--brief must contain the actual request")
    try:
        brief = make_brief(args.intent, args.brief)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8") as output:
            output.write(brief)
    except FileExistsError:
        parser.error(f"Existing design brief preserved: {args.out}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build a portable A/B comparison page with an optional design reference."""

import argparse
from base64 import b64encode
from html import escape
import json
from pathlib import Path


VIEWPORTS = {"desktop": [1440, 900], "mobile": [390, 844]}


def read_review(path):
    report = json.loads(path.read_text(encoding="utf-8"))
    profiles = {profile["profile"]: profile for profile in report.get("profiles", [])}
    images = {}
    for name, viewport in VIEWPORTS.items():
        profile = profiles.get(name, {})
        screenshot = profile.get("screenshot")
        if profile.get("layout", {}).get("viewport") != viewport or not screenshot:
            raise ValueError(f"{path} has no {name} capture at {viewport[0]}×{viewport[1]}")
        if screenshot != f"{name}.png":
            raise ValueError(f"Expected the sibling {name}.png capture in {path}")
        image_path = path.with_name(screenshot)
        data = image_path.read_bytes()
        expected_size = (int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big"))
        if not data.startswith(b"\x89PNG\r\n\x1a\n") or expected_size != tuple(viewport):
            raise ValueError(f"{image_path} is not a PNG at the declared viewport")
        images[name] = b64encode(data).decode("ascii")
    return report, images


def make_board(path_a, path_b, brief, reference=None):
    variants = [("方案 A", read_review(path_a)), ("方案 B", read_review(path_b))]
    settle_a, settle_b = (report.get("settle_ms") for _, (report, _) in variants)
    if settle_a is None or settle_a != settle_b:
        raise ValueError("Capture both variants with review_site.mjs using the same --settle-ms.")
    columns = variants
    if reference is not None:
        columns = [("视觉参考", read_review(reference)), *variants]
    sections = []
    for name, (width, height) in VIEWPORTS.items():
        figures = []
        for label, (_, images) in columns:
            figures.append(f'<figure><figcaption>{label}</figcaption>'
                           f'<img src="data:image/png;base64,{images[name]}" '
                           f'width="{width}" height="{height}" alt="{label} 的{name}首屏"></figure>')
        sections.append(f'<section><h2>{width}×{height}</h2><div class="pair">{"".join(figures)}</div></section>')
    statuses = " · ".join(f"{label} {escape(report['status'])}" for label, (report, _) in variants)
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sitecraft 首屏对照</title>
<style>
body{{max-width:1600px;margin:auto;padding:24px;color:#202022;background:#f7f7f5;font:16px/1.55 system-ui,sans-serif}}
h1,h2{{line-height:1.2}}p{{max-width:70ch;white-space:pre-wrap}}
.pair{{display:grid;grid-template-columns:repeat({len(columns)},minmax(0,1fr));gap:16px}}
@media(max-width:700px){{
  .with-reference .pair{{grid-template-columns:repeat(2,minmax(0,1fr))}}
  .with-reference .pair > :first-child{{grid-column:1/-1}}
}}
figure{{margin:0;text-align:center}}img{{display:block;max-width:100%;height:auto;margin:8px auto 0;border:1px solid #d8d8d6}}
section{{margin-block:32px}}details{{border-top:1px solid #d8d8d6;padding-top:12px}}
</style></head><body class="{'with-reference' if reference is not None else ''}">
<h1>首屏对照</h1><p>{escape(brief)}</p>
{"".join(sections)}
<details><summary>浏览器检查结果</summary><p>{statuses}。视觉取舍需查看实际画面。</p></details>
</body></html>
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("review_a", type=Path)
    parser.add_argument("review_b", type=Path)
    parser.add_argument("--reference", type=Path, help="Optional separate desktop/mobile review.json for the visual reference.")
    parser.add_argument("--brief", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        board = make_board(args.review_a, args.review_b, args.brief, args.reference)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8") as output:
            output.write(board)
    except (OSError, ValueError, KeyError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()

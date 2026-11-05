"""Original static-site sections. Data comes from the current project, never invented metrics."""
import html
from pathlib import Path
import re
from urllib.parse import urlsplit


def require(condition, message):
    if not condition:
        raise ValueError(message)

TYPES = ('collection', 'services', 'story', 'contact', 'workspace')
RESERVED = {'hero-title', 'site-menu', 'contact-dialog', 'contact-form', 'contact-result'}


def text(value):
    return html.escape(str(value), quote=True)


def label(obj, key):
    value = obj.get(key)
    require(isinstance(value, str) and value.strip(), f'Section requires {key}')
    return value


def href(value, ids):
    require(isinstance(value, str) and value.strip(), 'Action needs a real destination')
    if value.startswith('#'):
        require(value[1:] in ids, f'Missing section destination: {value}')
    else:
        parsed = urlsplit(value)
        require(parsed.scheme in ('https', 'http', 'mailto', 'tel') and not parsed.username and not parsed.password,
                'Use an ordinary web, mail or phone action without embedded credentials')
        require(bool(parsed.netloc or parsed.path), 'Empty action destination')
    return value


def validate_sections(config, base, extra_ids=()):
    require(isinstance(config, dict), 'Section configuration must be an object')
    sections = config.get('sections')
    require(isinstance(sections, list) and sections, 'Supply actual sections for the complete site')
    ids = set(extra_ids)
    for section in sections:
        require(isinstance(section, dict) and section.get('type') in TYPES, 'Unsupported section type')
        name = label(section, 'id')
        require(re.fullmatch(r'[a-z][a-z0-9-]*', name) and name not in RESERVED and name not in ids, 'Use unique section IDs')
        ids.add(name)
        label(section, 'title')
    require(sum(section['type'] == 'contact' for section in sections) <= 1, 'Use one shared contact destination')
    for section in sections:
        kind = section['type']
        if kind in ('collection', 'services'):
            require(isinstance(section.get('items'), list) and section['items'], 'Supply actual collection/service items')
            for item in section['items']:
                require(isinstance(item, dict), 'Items must be objects')
                label(item, 'name')
                label(item, 'description')
                if item.get('action'):
                    label(item['action'], 'label')
                    href(label(item['action'], 'href'), ids)
                if item.get('image'):
                    source = (base / item['image']).resolve()
                    require(source.is_file() and source.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp', '.avif', '.svg'), 'Use a local section image')
                    label(item, 'alt')
                    label(item, 'origin')
        elif kind == 'workspace':
            render_workspace(section)
        else:
            label(section, 'body')
        if kind == 'contact':
            require(section.get('demo') is True or isinstance(section.get('methods'), list) and section['methods'],
                    'Provide real contact methods or an explicitly marked local demonstration')
            for method in section.get('methods', []):
                label(method, 'label')
                href(label(method, 'href'), ids)
    for link in config.get('navigation', []):
        label(link, 'label')
        href(label(link, 'href'), ids)
    return ids


def render_workspace(config):
    require(isinstance(config, dict), 'Supply a workspace data object')
    label(config, 'title')
    items = config.get('items')
    require(isinstance(items, list) and items, 'Workspace needs actual demo tasks or documents')
    buttons = []
    for index, item in enumerate(items):
        require(isinstance(item, dict), 'Workspace items must be objects')
        title, body = label(item, 'name'), label(item, 'body')
        buttons.append(f'<button type="button" class="workspace-item" data-work-item data-title="{text(title)}" data-body="{text(body)}" aria-pressed="{"true" if index == 0 else "false"}"><span>{text(item.get("kind", "事项"))}</span><strong>{text(title)}</strong></button>')
    return f'''<div class="workspace" data-workspace><div class="workspace-heading"><strong>{text(config['title'])}</strong><span>本地演示</span></div>
<div class="workspace-grid"><nav aria-label="演示事项">{''.join(buttons)}</nav><article class="workspace-detail" aria-live="polite"><span class="workspace-kicker">当前事项</span><h3>{text(items[0]['name'])}</h3><p class="workspace-body">{text(items[0]['body'])}</p><p class="workspace-note">示例内容可在本页切换，不连接真实工作空间。</p></article></div></div>'''


def render_parts(config, base, primary_target, brand, extra_ids=()):
    """Return HTML and source->destination media copies; no files are written here."""
    ids = validate_sections(config, base, extra_ids)
    href(primary_target, ids)
    assets, sections_html = [], []
    nav = config.get('navigation') or [{'label': item.get('nav_label', item['title']), 'href': '#' + item['id']}
                                       for item in config['sections']]
    links = ''.join(f'<a href="{text(item["href"])}">{text(item["label"])}</a>' for item in nav)
    header = f'''<header class="site-header"><a class="wordmark" href="./">{text(brand)}</a>
<nav class="desktop-nav" aria-label="主导航">{links}</nav><button class="menu-button" data-open-menu aria-controls="site-menu" aria-expanded="false" type="button">菜单<span aria-hidden="true">＋</span></button></header>
<dialog id="site-menu" class="menu-dialog" aria-label="网站导航"><div class="dialog-heading"><span>{text(brand)}</span><button data-close-dialog type="button" aria-label="关闭菜单">关闭</button></div><nav aria-label="手机导航">{links}</nav></dialog>'''
    for section in config['sections']:
        kind, name = section['type'], section['id']
        intro = f'<p class="section-intro">{text(section["intro"])}</p>' if section.get('intro') else ''
        heading = f'<div class="section-heading"><h2 id="{name}-title">{text(section["title"])}</h2>{intro}</div>'
        if kind in ('collection', 'services'):
            items = []
            for index, item in enumerate(section['items']):
                picture = ''
                if item.get('image'):
                    source = (base / item['image']).resolve()
                    filename = f'section-{name}-{index + 1}{source.suffix.lower()}'
                    assets.append((source, filename))
                    picture = f'<div class="item-image"><img src="assets/{filename}" alt="{text(item["alt"])}" loading="lazy"></div>'
                price = f'<p class="item-price">{text(item["price"])}</p>' if item.get('price') else ''
                action = item.get('action')
                link = f'<a class="text-action" href="{text(action["href"])}">{text(action["label"])}<span aria-hidden="true">↗</span></a>' if action else ''
                items.append(f'<article class="site-item">{picture}<div class="item-copy"><h3>{text(item["name"])}</h3><p>{text(item["description"])}</p>{price}{link}</div></article>')
            body = f'<div class="{kind}-items">{"".join(items)}</div>'
        elif kind == 'workspace':
            body = render_workspace(section)
        elif kind == 'story':
            body = f'<div class="story-copy"><p>{text(section["body"])}</p></div>'
        else:
            methods = ''.join(f'<a class="contact-method" href="{text(item["href"])}">{text(item["label"])}</a>' for item in section.get('methods', []))
            demo = '<button class="primary" type="button" data-open-contact>体验咨询流程</button><p class="demo-note">本地演示，不发送咨询或生成订单。</p>' if section.get('demo') else ''
            body = f'<div class="contact-copy"><p>{text(section["body"])}</p><div class="contact-actions">{methods}{demo}</div></div>'
        sections_html.append(f'<section class="site-section section-{kind}" id="{name}" aria-labelledby="{name}-title">{heading}{body}</section>')
    footer = f'<footer class="site-footer"><a class="wordmark" href="./">{text(brand)}</a><p>{text(config.get("footer_note", ""))}</p><a href="#hero-title">回到顶部 ↑</a></footer>'
    dialog = '''<dialog id="contact-dialog" class="contact-dialog" aria-labelledby="contact-title"><div class="dialog-heading"><h2 id="contact-title">整理这次咨询</h2><button type="button" data-close-dialog aria-label="关闭咨询">关闭</button></div>
<p>填写后预览你的留言。本地演示不会发送或保存个人信息。</p><form id="contact-form"><label>如何称呼你<input name="name" autocomplete="name" maxlength="40" required></label><label>想咨询什么<textarea name="message" rows="4" maxlength="500" required></textarea></label><button class="primary" type="submit">预览留言</button><output id="contact-result" aria-live="polite"></output></form></dialog>'''
    if not any(section['type'] == 'contact' and section.get('demo') for section in config['sections']):
        dialog = ''
    return {'header': header, 'sections': '\n'.join(sections_html), 'footer': footer, 'dialog': dialog, 'assets': assets}

# Django HiHi Footer

Adds a **HiHi Labs** branding footer to any Django admin panel.

Built by [HiHi Labs](https://hihi.communityplaylist.com/portfolio.html) — Portland, OR.

## What it looks like

```
◉  Built by HiHi Labs · Hosted at Community Playlist
```

Styled in monospace, subtle `#555` with `#ff6b35` accent on the ◉ and the HiHi Labs link.
The ◉ links to the HiHi Labs portfolio page.

## Install

**Option A — copy manually:**

```bash
cp templates/admin/base_site.html your_project/templates/admin/base_site.html
```

**Option B — install script:**

```bash
TEMPLATES_DIR=your_project/templates bash install.sh
```

**Option C — extend it yourself** (if you already have a `base_site.html`):

Add this block to your existing `templates/admin/base_site.html`:

```django
{% block footer %}
{{ block.super }}
<div style="text-align:center;padding:10px 24px 14px;border-top:1px solid rgba(255,255,255,.06);font-size:.78em;color:#555;font-family:'Courier New',monospace">
  <a href="https://hihi.communityplaylist.com/portfolio.html" target="_blank"
     style="color:#ff6b35;text-decoration:none;font-weight:700;font-size:1.1em"
     title="HiHi Labs Portfolio">◉</a>
  &nbsp;Built by
  <a href="https://hihi.communityplaylist.com" target="_blank"
     style="color:#ff6b35;text-decoration:none;font-weight:600">HiHi Labs</a>
  &nbsp;·&nbsp;
  Hosted at
  <a href="https://communityplaylist.com" target="_blank"
     style="color:#555;text-decoration:none">Community Playlist</a>
</div>
{% endblock %}
```

## Requirements

- Django 3.2+ (tested on 4.2)
- Django admin enabled

## No `INSTALLED_APPS` changes needed

Django's template loader picks up `templates/admin/base_site.html` automatically as long as your templates directory is in `TEMPLATES[0]['DIRS']` or you're using `APP_DIRS = True` with a local `templates/` folder.

## Customizing

Edit the links in `templates/admin/base_site.html` to point to your own portfolio and hosting site.

## License

MIT

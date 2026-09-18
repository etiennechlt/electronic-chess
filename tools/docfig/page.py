"""Common furniture of the pages of `docs/pages/`: the style sheet, the web
fonts, the figure wrapper, the document skeleton and the checks.

The pages double the notes 18, 19 and 20 for a reader who opens a browser
rather than a repository: same prose, same numbers (computed by
chessboard_calc from config/board.yaml, never written by hand) and the
same figures as `docs/images/`, drawn by the other modules of this
package and embedded so that a page is one self-contained file.
"""

from __future__ import annotations

import re

CSS = r"""
:root{
  --bg:#f3f5f2; --surface:#ffffff; --ink:#1a1e1d; --ink-2:#4f5754; --ink-3:#7d8582; --rule:#d3d8d4;
  --q-high:#2a78d6; --q-low:#eb6834; --band:rgba(42,120,214,.09); --tint:#e9eef4;
  --wood:#e6d3b1; --felt:#c9ccc4; --air:#f7f9f7; --pcb:#c4d9c0; --copper:#c8843a; --magnet:#8b8f92; --piece:#efe6d6;
  color-scheme:light;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#15191a; --surface:#1e2324; --ink:#e8ecea; --ink-2:#a8b0ac; --ink-3:#7c8582; --rule:#343d3b;
    --q-high:#3987e5; --q-low:#d95926; --band:rgba(57,135,229,.14); --tint:#232b30;
    --wood:#6b5836; --felt:#4a4f4b; --air:#1b2021; --pcb:#2f4a33; --copper:#d0894a; --magnet:#6b7073; --piece:#3a3630;
    color-scheme:dark;
  }
}
:root[data-theme="dark"]{
  --bg:#15191a; --surface:#1e2324; --ink:#e8ecea; --ink-2:#a8b0ac; --ink-3:#7c8582; --rule:#343d3b;
  --q-high:#3987e5; --q-low:#d95926; --band:rgba(57,135,229,.14); --tint:#232b30;
  --wood:#6b5836; --felt:#4a4f4b; --air:#1b2021; --pcb:#2f4a33; --copper:#d0894a; --magnet:#6b7073; --piece:#3a3630;
  color-scheme:dark;
}
body{background:var(--bg); color:var(--ink); font-family:"IBM Plex Sans","Segoe UI",Roboto,Helvetica,Arial,sans-serif; font-size:16px; line-height:1.55; margin:0;}
.wrap{max-width:920px; margin:0 auto; padding-block:40px 64px; padding-inline:16px;}
h1,h2{font-family:"Bricolage Grotesque","IBM Plex Sans",Helvetica,Arial,sans-serif; text-wrap:balance; line-height:1.1; margin:0;}
h1{font-size:clamp(2.4rem,6vw,3.6rem); font-weight:700; letter-spacing:-.01em;}
h2{font-size:clamp(1.45rem,3vw,1.9rem); font-weight:600; margin-top:.2em;}
.eyebrow{font-family:"IBM Plex Mono",Menlo,Consolas,monospace; font-size:.74rem; letter-spacing:.14em; text-transform:uppercase; color:var(--ink-3); margin:0 0 .5rem;}
.lede{font-size:1.2rem; line-height:1.5; color:var(--ink-2); max-width:62ch; margin:1rem 0 0;}
p{max-width:68ch; margin:.9rem 0;}
ul,ol{max-width:68ch; padding-left:1.2rem;}
li{margin:.35rem 0;}
section{margin-top:3.2rem; padding-top:2rem; border-top:1px solid var(--rule);}
.keep{margin-top:2rem; background:var(--surface); border:1px solid var(--rule); border-left:4px solid var(--q-high); padding:1rem 1.2rem; border-radius:6px; max-width:68ch;}
.keep p{margin:.3rem 0;}
.keep strong{color:var(--q-high);}
figure{margin:1.6rem 0 0;}
.fig-scroll{overflow-x:auto; position:relative; background:var(--surface); border:1px solid var(--rule); border-radius:8px; padding:12px 8px;}
.fig-scroll svg{display:block; width:100%; min-width:640px; height:auto; color:var(--ink); font-family:"IBM Plex Sans",Helvetica,Arial,sans-serif;}
figcaption{font-size:.92rem; color:var(--ink-2); margin-top:.6rem; max-width:72ch;}
figcaption b{color:var(--ink);}
svg .lbl{font-size:12.5px; fill:var(--ink);}
svg .lbl.small{font-size:11px;}
svg .lbl.strong{font-weight:600;}
svg .muted{fill:var(--ink-2);}
svg .mono{font-family:"IBM Plex Mono",Menlo,Consolas,monospace;}
svg .glyph{font-size:20px; font-family:"Segoe UI Symbol","Apple Symbols","Noto Sans Symbols 2","DejaVu Sans",sans-serif;}
svg .title{font-size:14px; font-weight:600; fill:var(--ink);}
svg .axis{stroke:currentColor; stroke-width:1.2; fill:none; opacity:.55;}
svg .tick{stroke:currentColor; stroke-width:1; opacity:.55;}
svg .grid{stroke:currentColor; stroke-width:1; opacity:.12;}
svg .dash{stroke:currentColor; stroke-width:1; stroke-dasharray:5 4; opacity:.5; fill:none;}
svg .brk{stroke:currentColor; stroke-width:1.2; opacity:.6; fill:none;}
svg .trace{fill:none; stroke-width:2; stroke-linejoin:round; stroke-linecap:round;}
svg .trace.ghost{opacity:.35; stroke-dasharray:3 3;}
svg .env{fill:none; stroke-width:1.2; stroke-dasharray:4 4; opacity:.7;}
svg .q-high{stroke:var(--q-high);}
svg .q-low{stroke:var(--q-low);}
svg .q-high-t{fill:var(--q-high); font-weight:600;}
svg .q-low-t{fill:var(--q-low); font-weight:600;}
svg .mark{stroke-width:1.6;}
svg .dot{fill:var(--surface); stroke-width:2.5;}
svg .band{fill:var(--band);}
svg .peak-black{fill:var(--q-high); stroke:var(--q-high); stroke-width:1.5; stroke-linejoin:round; opacity:.9;}
svg .peak-white{fill:var(--surface); stroke:var(--q-high); stroke-width:1.8; stroke-linejoin:round;}
svg .peak{cursor:default;}
svg .peak:hover .peak-black, svg .peak:hover .peak-white{stroke:var(--q-low);}
svg .tipbox{fill:var(--surface); stroke:var(--rule);}
svg .lay-pcb{fill:var(--pcb);} svg .lay-air{fill:var(--air);} svg .lay-wood{fill:var(--wood);} svg .lay-felt{fill:var(--felt);}
svg .copper{fill:var(--copper);}
svg .piece{fill:var(--piece); stroke:currentColor; stroke-width:1.2; opacity:.95;}
svg .bundle{fill:url(#wire); stroke:currentColor; stroke-width:1;}
svg .cap{fill:var(--q-low); stroke:none;}
svg .magnet{fill:var(--magnet); opacity:.75;}
svg .field{fill:none; stroke:var(--q-high); stroke-width:1.6; opacity:.8;}
svg .seg{fill:var(--tint); stroke:var(--rule);}
svg .seg-pulse{fill:var(--q-low); opacity:.35; stroke:var(--q-low);}
svg .seg-listen{fill:var(--band); stroke:var(--q-high);}
svg .box{fill:var(--surface); stroke:var(--rule); stroke-width:1.2;}
svg .box-piece{stroke:var(--q-high); stroke-width:1.8;}
svg .box-mcu{fill:var(--tint); stroke:var(--q-high); stroke-width:1.8;}
svg .box-soft{fill:var(--tint); stroke:var(--rule); stroke-width:1.2;}
svg .box-warm{fill:var(--surface); stroke:var(--q-low); stroke-width:1.6;}
svg .wire{stroke:currentColor; stroke-width:1.4; fill:none; opacity:.7;}
svg .wire-a{stroke:var(--q-high); stroke-width:2; fill:none;}
svg .wire-p{stroke:var(--q-low); stroke-width:2; fill:none;}
svg .zone{fill:none; stroke:var(--rule); stroke-width:1.2; stroke-dasharray:6 4;}
svg .coil{fill:none; stroke:var(--copper); stroke-width:2;}
svg .puck{fill:var(--piece); stroke:currentColor; stroke-width:1.2;}
.tip{position:absolute; pointer-events:none; background:var(--surface); color:var(--ink); border:1px solid var(--rule); border-radius:6px; padding:.45rem .6rem; font-size:.84rem; line-height:1.35; box-shadow:0 4px 14px rgba(0,0,0,.12); max-width:260px; z-index:2;}
.formulas{display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:12px; margin:1.2rem 0; max-width:900px;}
.formula{background:var(--surface); border:1px solid var(--rule); border-radius:8px; padding:.8rem .95rem;}
.formula .f{font-family:"IBM Plex Mono",Menlo,Consolas,monospace; font-size:1.02rem; margin:0 0 .35rem; color:var(--ink);}
.formula .d{font-size:.88rem; color:var(--ink-2); margin:0;}
table{border-collapse:collapse; width:100%; font-size:.9rem; margin-top:1rem; font-variant-numeric:tabular-nums;}
th,td{padding:.42rem .55rem; border-bottom:1px solid var(--rule); text-align:left; vertical-align:top;}
td.n,th.n{text-align:right; white-space:nowrap;}
th{font-family:"IBM Plex Mono",Menlo,Consolas,monospace; font-size:.74rem; letter-spacing:.06em; text-transform:uppercase; color:var(--ink-3); font-weight:500;}
.tbl{overflow-x:auto;}
dl{display:grid; grid-template-columns:max-content 1fr; gap:.5rem 1.2rem; max-width:80ch; margin:1rem 0 0;}
dt{font-weight:600; color:var(--ink);}
dd{margin:0; color:var(--ink-2);}
@media (max-width:560px){ dl{grid-template-columns:1fr;} dd{margin-bottom:.5rem;} }
.foot{margin-top:3rem; padding-top:1rem; border-top:1px solid var(--rule); font-size:.84rem; color:var(--ink-3); max-width:72ch;}
code{font-family:"IBM Plex Mono",Menlo,Consolas,monospace; font-size:.9em; background:var(--tint); padding:.05em .3em; border-radius:3px;}
"""

FONTS = (
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:'
    "opsz,wght@12..96,500;12..96,700&family=IBM+Plex+Sans:wght@400;500;600"
    '&family=IBM+Plex+Mono:wght@400;500&display=swap">'
)


def fig(svg: str, caption: str, fig_id: str = "", tip: bool = False) -> str:
    idattr = f' id="{fig_id}"' if fig_id else ""
    tipdiv = f'<div class="tip" id="tip-{fig_id}" hidden></div>' if tip else ""
    return (
        f'<figure><div class="fig-scroll"{idattr}>{svg}{tipdiv}</div>'
        f"<figcaption>{caption}</figcaption></figure>"
    )


def check(page: str) -> None:
    assert "{{" not in page, re.findall(r"\{\{[A-Z_0-9]+\}\}", page)[:5]
    assert chr(0x2014) not in page and chr(0x2013) not in page, "dash found"


def esc(text: str) -> str:
    """Text into an HTML fragment."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def document(title: str, body: str, script: str = "") -> str:
    """A complete page: the fragment of a builder in its skeleton."""
    return (
        '<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{title}</title>\n" + FONTS + "\n<style>" + CSS + "</style>\n"
        "</head>\n<body>\n" + body + script + "</body>\n</html>\n"
    )

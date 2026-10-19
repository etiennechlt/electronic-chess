"""Pages rendered from a Markdown document of `docs/` itself: the two
demonstrator tutorials (notes 26 and 27), the cost sheet and the priced
bills of materials. Where the pages of notes 18 to 24 are HTML twins
written alongside their note, these take the note as their single
source: the same text, rendered into the same skeleton, style sheet and
figure wrapper as the other pages, SVG figures inlined and renders
embedded, so that one file travels alone.

The renderer covers the Markdown the notes use: headings, paragraphs,
bullet and numbered lists, tables, fenced code, images, links, code
spans, bold and italics. Relative links to other documents of the
repository point at the published copy on GitHub, except the notes that
have a page of their own, which link to that page.
"""

from __future__ import annotations

import base64
import re
from pathlib import Path

from chessboard_calc.config import DEFAULT_CONFIG_PATH, BoardConfig

from .page import check, document

REPO = DEFAULT_CONFIG_PATH.parents[1]
GITHUB = "https://github.com/etiennechlt/electronic-chess/blob/main/"

# the Markdown documents that have a page, by their path under docs/
NOTE_PAGES: dict[str, str] = {
    "notes/18-facteur-q.md": "facteur-q.html",
    "notes/19-cerveau-et-banc-nucleo.md": "cerveau-banc.html",
    "notes/20-tuto-banc.md": "tuto-banc.html",
    "notes/24-hall-et-rfid.md": "hall-rfid.html",
    "notes/26-demonstrateur-lc.md": "demonstrateur-lc.html",
    "notes/27-demonstrateur-hall-rfid.md": "demonstrateur-hall-rfid.html",
    "couts-demonstrateurs.md": "couts-demonstrateurs.html",
    "bom-demonstrateur-a.md": "bom-demonstrateur-a.html",
    "bom-demonstrateur-b.md": "bom-demonstrateur-b.html",
}

# the documents rendered by this module, with the eyebrow of their title
RENDERED: dict[str, tuple[str, str]] = {
    "demonstrateur-lc.html": ("notes/26-demonstrateur-lc.md", "Démonstrateur A, note 26"),
    "demonstrateur-hall-rfid.html": (
        "notes/27-demonstrateur-hall-rfid.md",
        "Démonstrateur B, note 27",
    ),
    "couts-demonstrateurs.html": ("couts-demonstrateurs.md", "Les deux démonstrateurs"),
    "bom-demonstrateur-a.html": ("bom-demonstrateur-a.md", "Démonstrateur A"),
    "bom-demonstrateur-b.html": ("bom-demonstrateur-b.md", "Démonstrateur B"),
}

EXTRA_CSS = r"""
h3{font-family:"Bricolage Grotesque","IBM Plex Sans",Helvetica,Arial,sans-serif; font-size:1.2rem; font-weight:600; margin:1.8rem 0 0; text-wrap:balance;}
pre{background:var(--tint); border:1px solid var(--rule); border-radius:8px; padding:.8rem 1rem; overflow-x:auto; font-size:.84rem; line-height:1.45; max-width:100%;}
pre code{background:none; padding:0; font-size:inherit;}
.shot{display:block; width:100%; height:auto; border-radius:8px; border:1px solid var(--rule); background:var(--surface);}
.keep ul,.keep ol{margin:.4rem 0 0; padding-left:1.1rem;}
.keep li{margin:.3rem 0;}
blockquote{margin:1rem 0; padding:.2rem 1rem; border-left:4px solid var(--rule); color:var(--ink-2); max-width:68ch;}
blockquote p{margin:.4rem 0;}
td a,th a{color:var(--q-high); text-decoration:none;} td a:hover{text-decoration:underline;}
.wrap a{color:var(--q-high);}
"""

NUM_CLASS = ' class="n"'
_NUM = re.compile(r"^[\s\d.,%*x/±+-]+$")


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Renderer:
    def __init__(self, md_path: Path, repo: Path = REPO):
        self.path = md_path
        self.repo = repo
        self.base = md_path.parent
        self.svg_count = 0

    # ---- links and images -------------------------------------------------

    def href(self, url: str) -> str:
        if url.startswith(("http://", "https://", "mailto:", "#")):
            return url
        target, _, anchor = url.partition("#")
        resolved = (self.base / target).resolve()
        try:
            rel = resolved.relative_to((self.repo / "docs").resolve()).as_posix()
        except ValueError:
            rel = ""
        if rel in NOTE_PAGES:
            return NOTE_PAGES[rel] + (f"#{anchor}" if anchor else "")
        try:
            repo_rel = resolved.relative_to(self.repo.resolve()).as_posix()
        except ValueError:
            return url
        return GITHUB + repo_rel + (f"#{anchor}" if anchor else "")

    def figure(self, alt: str, src: str) -> str:
        path = (self.base / src).resolve()
        caption = f"<figcaption><b>{self.inline(alt)}</b></figcaption>" if alt else ""
        if path.suffix == ".svg" and path.exists():
            svg = path.read_text(encoding="utf-8")
            svg = re.sub(r"<\?xml[^>]*\?>\s*", "", svg)
            svg = re.sub(r"<!DOCTYPE[^>]*>\s*", "", svg)
            self.svg_count += 1
            return f'<figure><div class="fig-scroll">{svg.strip()}</div>{caption}</figure>'
        if path.suffix == ".png" and path.exists():
            data = base64.b64encode(path.read_bytes()).decode("ascii")
            return (
                f'<figure><img class="shot" alt="{esc(alt)}" loading="lazy" '
                f'src="data:image/png;base64,{data}">{caption}</figure>'
            )
        return f'<figure><a href="{self.href(src)}">{self.inline(alt) or esc(src)}</a></figure>'

    # ---- inline -----------------------------------------------------------

    def inline(self, text: str) -> str:
        """Code spans are set aside (their content is literal), the rest is
        escaped and marked up, then the spans come back as <code>: a link
        or a bold run may wrap a span."""
        spans: list[str] = []

        def keep(m: re.Match) -> str:
            spans.append(f"<code>{esc(m.group(1))}</code>")
            return f"\x00{len(spans) - 1}\x00"

        s = re.sub(r"`([^`]+)`", keep, text)
        s = self._markup(esc(s))
        return re.sub(r"\x00(\d+)\x00", lambda m: spans[int(m.group(1))], s)

    def _markup(self, s: str) -> str:
        s = re.sub(
            r"!\[([^\]]*)\]\(([^)\s]+)\)",
            lambda m: f'<a href="{self.href(m.group(2))}">{m.group(1)}</a>',
            s,
        )
        s = re.sub(
            r"\[([^\]]+)\]\(([^)\s]+)\)",
            lambda m: f'<a href="{self.href(m.group(2))}">{m.group(1)}</a>',
            s,
        )
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
        return s

    # ---- blocks -----------------------------------------------------------

    def table(self, lines: list[str]) -> str:
        rows = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in lines]
        rows = [r for r in rows if not all(re.fullmatch(r":?-+:?", c or "-") for c in r)]
        if not rows:
            return ""
        head, body = rows[0], rows[1:]
        numeric = [
            all(_NUM.match(r[i]) for r in body if i < len(r) and r[i])
            and any(i < len(r) and r[i] for r in body)
            for i in range(len(head))
        ]
        th = "".join(
            f"<th{NUM_CLASS if numeric[i] else ''}>{self.inline(c)}</th>"
            for i, c in enumerate(head)
        )
        trs = []
        for r in body:
            tds = "".join(
                f"<td{NUM_CLASS if i < len(numeric) and numeric[i] else ''}>{self.inline(c)}</td>"
                for i, c in enumerate(r)
            )
            trs.append(f"<tr>{tds}</tr>")
        return f'<div class="tbl"><table><thead><tr>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'

    def list_block(self, items: list[str], ordered: bool, lexicon: bool) -> str:
        if lexicon:
            dl = []
            for it in items:
                m = re.match(r"\*\*(.+?)\*\*\s*:\s*(.*)", it, re.S)
                if not m:
                    lexicon = False
                    break
                dl.append(f"<dt>{self.inline(m.group(1))}</dt><dd>{self.inline(m.group(2))}</dd>")
            if lexicon:
                return f"<dl>{''.join(dl)}</dl>"
        tag = "ol" if ordered else "ul"
        return f"<{tag}>" + "".join(f"<li>{self.inline(it)}</li>" for it in items) + f"</{tag}>"

    def render(self) -> tuple[str, str]:
        """(title, body fragment)."""
        lines = self.path.read_text(encoding="utf-8").splitlines()
        title = ""
        lede_done = False
        out: list[str] = []
        in_section = False
        keep_open = False
        lexicon = False
        i = 0
        n = len(lines)

        def close_keep() -> None:
            nonlocal keep_open
            if keep_open:
                out.append("</div>")
                keep_open = False

        while i < n:
            ln = lines[i]
            s = ln.strip()
            if not s:
                i += 1
                continue
            if s.startswith("```"):
                j = i + 1
                code = []
                while j < n and not lines[j].strip().startswith("```"):
                    code.append(lines[j])
                    j += 1
                out.append(f"<pre><code>{esc(chr(10).join(code))}</code></pre>")
                i = j + 1
                continue
            m = re.match(r"^(#{1,6})\s+(.*)$", s)
            if m:
                level, text = len(m.group(1)), m.group(2).strip()
                close_keep()
                if level == 1:
                    title = re.sub(r"^\d+\.\s+", "", text)
                    out.append(f"<h1>{self.inline(title)}</h1>")
                elif level == 2:
                    if in_section:
                        out.append("</section>")
                    num = re.match(r"^(\d+)\.\s+(.*)$", text)
                    eyebrow = f"Partie {num.group(1)}" if num else ""
                    text = num.group(2) if num else text
                    lexicon = "lexique" in text.lower()
                    out.append("<section>")
                    if eyebrow:
                        out.append(f'<p class="eyebrow">{eyebrow}</p>')
                    out.append(f"<h2>{self.inline(text)}</h2>")
                    in_section = True
                else:
                    text = re.sub(r"^\d+(\.\d+)*\s+", "", text)
                    out.append(f"<h3>{self.inline(text)}</h3>")
                i += 1
                continue
            if s.startswith("|"):
                j = i
                while j < n and lines[j].strip().startswith("|"):
                    j += 1
                out.append(self.table(lines[i:j]))
                i = j
                continue
            if s.startswith(">"):
                j = i
                quote = []
                while j < n and lines[j].strip().startswith(">"):
                    quote.append(lines[j].strip()[1:].strip())
                    j += 1
                out.append(f"<blockquote><p>{self.inline(' '.join(quote))}</p></blockquote>")
                i = j
                continue
            m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", ln)
            if m:
                ordered = m.group(2)[0].isdigit()
                items: list[str] = []
                j = i
                while j < n:
                    mm = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", lines[j])
                    if mm and len(mm.group(1)) <= len(m.group(1)):
                        items.append(mm.group(3))
                        j += 1
                        continue
                    if lines[j].strip() and (lines[j].startswith(" ") or lines[j].startswith("\t")):
                        items[-1] += " " + lines[j].strip()
                        j += 1
                        continue
                    if not lines[j].strip() and j + 1 < n and lines[j + 1].startswith("   "):
                        # a blank line inside an item (a fenced block follows)
                        k = j + 1
                        if lines[k].strip().startswith("```"):
                            code = []
                            k += 1
                            while k < n and not lines[k].strip().startswith("```"):
                                code.append(lines[k].strip())
                                k += 1
                            items[-1] += f"<pre><code>{esc(chr(10).join(code))}</code></pre>"
                            j = k + 1
                            continue
                        j += 1
                        continue
                    break
                rendered = [
                    self.inline(it) if "<pre>" not in it else self._item_with_code(it)
                    for it in items
                ]
                if lexicon and not ordered:
                    out.append(self.list_block(items, ordered, True))
                else:
                    tag = "ol" if ordered else "ul"
                    out.append(
                        f"<{tag}>" + "".join(f"<li>{r}</li>" for r in rendered) + f"</{tag}>"
                    )
                close_keep()
                i = j
                continue
            m = re.match(r"^!\[([^\]]*)\]\(([^)\s]+)\)\s*$", s)
            if m:
                out.append(self.figure(m.group(1), m.group(2)))
                i += 1
                continue
            # a paragraph: consecutive non-blank, non-block lines
            j = i
            para = []
            while (
                j < n
                and lines[j].strip()
                and not re.match(r"^(#{1,6}\s|\||>|```|!\[|\s*([-*]|\d+\.)\s)", lines[j])
            ):
                para.append(lines[j].strip())
                j += 1
            text = " ".join(para)
            if title and not lede_done:
                out.append(f'<p class="lede">{self.inline(text)}</p>')
                lede_done = True
            elif text.rstrip(" :") in ("À retenir", "A retenir"):
                out.append('<div class="keep"><p><strong>À retenir.</strong></p>')
                keep_open = True
            else:
                out.append(f"<p>{self.inline(text)}</p>")
            i = j
        close_keep()
        if in_section:
            out.append("</section>")
        return title, "\n".join(out)

    def _item_with_code(self, item: str) -> str:
        """A list item holding a fenced block: prose around it is marked
        up, the block itself is kept as it is."""
        parts = re.split(r"(<pre>.*?</pre>)", item, flags=re.S)
        return "".join(part if part.startswith("<pre>") else self.inline(part) for part in parts)


def note_page(cfg: BoardConfig, name: str, repo: Path | None = None) -> str:
    repo = repo or REPO
    rel, eyebrow = RENDERED[name]
    md = repo / "docs" / rel
    r = Renderer(md, repo)
    title, body = r.render()
    body = body.replace("<h1>", f'<p class="eyebrow">{eyebrow}</p>\n<h1>', 1)
    foot = (
        f'<p class="foot">Page générée par <code>python -m docfig pages</code> depuis '
        f"<code>docs/{rel}</code> du dépôt electronic-chess : le même texte que le document, "
        "ses figures embarquées, ses chiffres calculés par <code>chessboard_calc</code> depuis "
        "<code>config/board.yaml</code> et épinglés par les tests du dépôt.</p>"
    )
    page = document(title, f'<div class="wrap">\n{body}\n{foot}\n</div>\n', extra_css=EXTRA_CSS)
    check(page)
    return page


def make_page(name: str):
    def fn(cfg: BoardConfig) -> str:
        return note_page(cfg, name)

    fn.__name__ = "page_" + name.replace("-", "_").replace(".html", "")
    return fn

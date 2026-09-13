#!/usr/bin/env python3
"""
Test suite for index.html + style.css (Escuelita Off Road).

Two parts:
  A. Structural tests  - confirms the HTML/CSS split is intact (no leftover
     bundle artifacts, stylesheet properly linked, local assets resolve).
  B. Mobile tests      - static checks against style.css/index.html for
     common responsive failure modes (missing mobile nav, text that is
     likely to overflow its container at small widths, etc).

There is no headless browser in this environment, so part B cannot render
the page. Widths marked WARN are computed from font-size formulas (clamp())
and an approximate glyph-width factor for the condensed display fonts used
here (Bebas Neue / Barlow Condensed) -- they are a heuristic, not a pixel
measurement. Treat WARN as "go look at this on a real phone", not as a
proven bug. FAIL means the defect is certain just from reading the code
(e.g. an element is unconditionally hidden with nothing to replace it).

Usage: python3 test_site.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = os.path.join(ROOT, "index.html")
CSS_PATH = os.path.join(ROOT, "style.css")

results = []  # (section, name, status, detail)  status in PASS/FAIL/WARN


def check(section, name, condition, detail_pass="", detail_fail=""):
    status = "PASS" if condition else "FAIL"
    results.append((section, name, status, detail_pass if condition else detail_fail))
    return condition


def warn(section, name, condition, detail):
    results.append((section, name, "WARN" if condition else "PASS", detail))


with open(HTML_PATH, encoding="utf-8") as f:
    html = f.read()
with open(CSS_PATH, encoding="utf-8") as f:
    css = f.read()

# HTML comments (e.g. the "replace with img/foto-X.jpg" authoring hint in the
# gallery section) contain example markup that isn't live -- strip comments
# before any structural pattern-matching so they can't skew the counts.
html_live = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)

# ─────────────────────────────────────────────────────────────
# A. STRUCTURAL: HTML/CSS split integrity
# ─────────────────────────────────────────────────────────────
SEC_A = "A. Structure"

check(SEC_A, "No <style> blocks left in index.html",
      "<style" not in html.lower(),
      "index.html has zero inline <style> tags.",
      "index.html still contains an inline <style> block.")

link_count = len(re.findall(r'<link[^>]+rel="stylesheet"[^>]+href="style\.css"', html))
check(SEC_A, "index.html links style.css exactly once",
      link_count == 1,
      "Found exactly one <link rel=\"stylesheet\" href=\"style.css\">.",
      f"Found {link_count} matching <link> tags (expected 1).")

check(SEC_A, "style.css is non-empty",
      len(css.strip()) > 0,
      f"style.css has {len(css)} bytes.",
      "style.css is empty.")

check(SEC_A, "No leftover __bundler artifacts",
      "__bundler" not in html,
      "No bundler manifest/template/loader script remains.",
      "index.html still contains __bundler script tags.")

uuid_re = re.compile(r'src="[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"')
leftover_uuids = uuid_re.findall(html_live)
check(SEC_A, "No asset-id placeholders left in <img src>",
      len(leftover_uuids) == 0,
      "All <img src> use real relative paths.",
      f"Found unresolved asset ids: {leftover_uuids}")

check(SEC_A, "Hero logo margin bug does not regress",
      "margin:46px 106px" not in html,
      "The stray margin that pushed the hero logo out of line is absent.",
      "The 'margin:46px 106px' regression is back on the hero logo.")

check(SEC_A, "Hero min-height is capped (no unbounded 100vh gap above the content)",
      "#hero{position:relative;min-height:100vh;" not in css and "min-height:min(100vh" in css,
      "#hero's min-height is capped, so tall viewports (desktop or portrait phones) can't "
      "push the bottom-anchored hero content down and leave a huge empty gap above it.",
      "#hero is back to an uncapped min-height:100vh -- tall viewports will show a large "
      "empty gap above the hero content again.")

# every local (non-http) src="" / href="" resolves to a real file on disk
local_refs = re.findall(r'(?:src|href)="([^"]+)"', html_live)
missing = []
for ref in local_refs:
    if ref.startswith(("http://", "https://", "#", "mailto:", "tel:")):
        continue
    if not os.path.exists(os.path.join(ROOT, ref)):
        missing.append(ref)
check(SEC_A, "All local asset references resolve to real files",
      len(missing) == 0,
      "Every local src/href points at a file that exists.",
      f"Missing local files: {missing}")

# crude open/close tag balance check for the common container tags
for tag in ["div", "section", "nav", "footer", "ul", "li", "a", "h1", "h2", "h3", "p", "form"]:
    opens = len(re.findall(rf"<{tag}(?=[ >])", html_live, re.IGNORECASE))
    closes = len(re.findall(rf"</{tag}>", html_live, re.IGNORECASE))
    check(SEC_A, f"<{tag}> open/close tags balance ({opens}/{closes})",
          opens == closes,
          f"{opens} open, {closes} close.",
          f"{opens} open vs {closes} close -- markup is unbalanced.")

# ─────────────────────────────────────────────────────────────
# B. MOBILE ADAPTATION
# ─────────────────────────────────────────────────────────────
SEC_B = "B. Mobile"

check(SEC_B, "Viewport meta tag present",
      'name="viewport"' in html and "width=device-width" in html,
      "viewport meta tag configured for device width.",
      "Missing <meta name=\"viewport\" content=\"width=device-width...\">.")

media_queries = re.findall(r"@media\(max-width:(\d+)px\)", css)
check(SEC_B, "Responsive breakpoints exist in style.css",
      len(media_queries) > 0,
      f"Breakpoints found: {media_queries}px.",
      "No @media rules found at all.")

# Nav: .nlinks must never be unconditionally hidden with nothing to replace it,
# and if a hamburger toggle exists it must actually be wired up (button in the
# markup, shown by CSS at the mobile breakpoint, and driven by JS).
check(SEC_B, "'.nlinks{display:none}' with no replacement is not present",
      ".nlinks{display:none}" not in css,
      "The old hide-with-nothing-to-replace-it rule is gone.",
      "@media(max-width:768px) still sets .nlinks{display:none} with nothing to replace it.")

has_burger_button = re.search(r'<button[^>]*id="nburger"', html_live) is not None
burger_shown_on_mobile = ".nburger{display:flex}" in css
nlinks_open_rule = ".nlinks.open{" in css
burger_wired_up = "getElementById('nburger')" in html_live and "nlinks.classList.toggle('open')" in html_live
check(SEC_B, "Mobile hamburger menu exists and is fully wired up",
      has_burger_button and burger_shown_on_mobile and nlinks_open_rule and burger_wired_up,
      "Button in markup, shown at the mobile breakpoint, CSS open-state rule present, "
      "and JS toggles it on click -- all four pieces are in place.",
      f"button={has_burger_button}, shown-on-mobile={burger_shown_on_mobile}, "
      f"open-rule={nlinks_open_rule}, js-wired={burger_wired_up} -- one or more pieces missing.")

# Heuristic text-overflow check using clamp() + an approximate glyph-width factor
# for condensed uppercase display fonts (Bebas Neue / Barlow Condensed).
GLYPH_WIDTH_FACTOR = 0.52  # approx average advance width as a fraction of font-size

def clamp_px(min_px, vw_pct, max_px, viewport_w):
    return max(min_px, min(max_px, viewport_w * vw_pct / 100))

WIDTHS = [320, 360, 375, 390, 414, 428]

def hc_padding(viewport_w):
    return 20 if viewport_w <= 768 else 40

HH_SMALL_PHONE_OVERRIDE = ".hh{font-size:clamp(52px,15vw,78px)}" in css
SGRID_SMALL_PHONE_OVERRIDE = "@media(max-width:480px)" in css and re.search(
    r"@media\(max-width:480px\)\{[^@]*\.sgrid\{grid-template-columns:1fr\}", css) is not None

for vw in WIDTHS:
    content_w = vw - 2 * hc_padding(vw)
    if vw <= 480 and HH_SMALL_PHONE_OVERRIDE:
        font = clamp_px(52, 15, 78, vw)
    else:
        font = clamp_px(78, 13, 190, vw)
    # worst-case single-line text after the <br>: "EL TERRENO" (10 chars incl. space)
    text_w = 10 * font * GLYPH_WIDTH_FACTOR
    warn(SEC_B, f"Hero title 'EL TERRENO' fits at {vw}px wide",
         text_w > content_w,
         f"font~{font:.0f}px -> estimated text width ~{text_w:.0f}px vs available {content_w}px "
         f"({'likely overflow/clip, verify on device' if text_w > content_w else 'fits comfortably'}).")

for vw in WIDTHS:
    section_pad = 24 if vw <= 1024 else 40
    section_content_w = vw - 2 * section_pad
    cols = 1 if (vw <= 480 and SGRID_SMALL_PHONE_OVERRIDE) else 2
    cell_w = (section_content_w - 1 * (cols - 1)) / cols  # 1px gap between columns
    cell_padding = 32
    cell_content_w = cell_w - 2 * cell_padding
    font = clamp_px(56, 6, 96, vw)
    text_w = 4 * font * GLYPH_WIDTH_FACTOR  # worst case "100%" / "100+"
    warn(SEC_B, f"Stats number (e.g. '100%') fits in its cell at {vw}px wide ({cols}-col grid)",
         text_w > cell_content_w,
         f"cell content ~{cell_content_w:.0f}px vs estimated number width ~{text_w:.0f}px "
         f"({'likely overflow/clip, verify on device' if text_w > cell_content_w else 'fits comfortably'}).")

check(SEC_B, "A dedicated small-phone breakpoint (<=480px) exists",
      any(int(m) <= 480 for m in media_queries),
      f"Found one at {[m for m in media_queries if int(m) <= 480]}px.",
      "Only breakpoints at " + str(media_queries) + "px exist -- nothing tuned specifically "
      "for small phones (~320-480px), which is where the WARNs above are most likely to bite.")

# ─────────────────────────────────────────────────────────────
# REPORT
# ─────────────────────────────────────────────────────────────
def print_section(section_name):
    rows = [r for r in results if r[0] == section_name]
    if not rows:
        return
    print(f"\n{section_name}")
    print("-" * len(section_name))
    for _, name, status, detail in rows:
        print(f"[{status:4}] {name}")
        if detail:
            print(f"       {detail}")

print_section(SEC_A)
print_section(SEC_B)

n_fail = sum(1 for r in results if r[2] == "FAIL")
n_warn = sum(1 for r in results if r[2] == "WARN")
n_pass = sum(1 for r in results if r[2] == "PASS")
print(f"\n{n_pass} passed, {n_warn} warnings, {n_fail} failed (of {len(results)} checks)")

sys.exit(1 if n_fail else 0)

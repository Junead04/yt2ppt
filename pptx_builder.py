# -*- coding: utf-8 -*-
"""Build PPTX from deck JSON using pptxgenjs via Node.js subprocess."""
import json
import os
import subprocess
import re
import tempfile


PALETTES = {
    "tech":      {"bg":"0F172A","bg2":"1E293B","accent":"6366F1","accent2":"8B5CF6","text":"F1F5F9","muted":"94A3B8","white":"FFFFFF","card":"252D3D","dark":"080D1A"},
    "business":  {"bg":"1A2744","bg2":"162038","accent":"F59E0B","accent2":"FBBF24","text":"F8FAFC","muted":"CBD5E1","white":"FFFFFF","card":"1F2E50","dark":"0F1829"},
    "education": {"bg":"FFFFFF","bg2":"F1F5F9","accent":"4F46E5","accent2":"7C3AED","text":"1E293B","muted":"64748B","white":"FFFFFF","card":"EEF2FF","dark":"1E293B"},
    "creative":  {"bg":"09090B","bg2":"18181B","accent":"EC4899","accent2":"F43F5E","text":"FAFAFA","muted":"A1A1AA","white":"FFFFFF","card":"27272A","dark":"000000"},
    "science":   {"bg":"022C22","bg2":"064E3B","accent":"10B981","accent2":"34D399","text":"ECFDF5","muted":"6EE7B7","white":"FFFFFF","card":"065F46","dark":"011A15"},
    "health":    {"bg":"F0F9FF","bg2":"E0F2FE","accent":"0EA5E9","accent2":"0284C7","text":"0F172A","muted":"475569","white":"FFFFFF","card":"BAE6FD","dark":"0C4A6E"},
}


def esc(s):
    if not s:
        return ""
    return str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", "").replace("\t", " ")


def build_script(deck: dict, out_path: str, images: dict, node_modules_path: str) -> str:
    theme = deck.get("theme", "tech")
    p = PALETTES.get(theme, PALETTES["tech"])
    slides = deck["slides"]
    title = esc(deck.get("title", "Presentation"))

    # Normalize path separators for Node.js (always use forward slashes)
    node_modules_path = node_modules_path.replace("\\", "/")
    out_path = out_path.replace("\\", "/")

    L = [
        f'const pptxgen = require("{node_modules_path}/pptxgenjs");',
        "const pres = new pptxgen();",
        "pres.layout = 'LAYOUT_16x9';",
        f'pres.title = "{title}";',
        "var slide;",
        "",
    ]

    def shape(x, y, w, h, color, alpha=None):
        a = f',transparency:{alpha}' if alpha is not None else ''
        L.append(f'  slide.addShape(pres.shapes.RECTANGLE,{{x:{x},y:{y},w:{w},h:{h},fill:{{color:"{color}"{a}}},line:{{color:"{color}"}}}});')

    def oval(x, y, w, h, color, alpha=80):
        L.append(f'  slide.addShape(pres.shapes.OVAL,{{x:{x},y:{y},w:{w},h:{h},fill:{{color:"{color}",transparency:{alpha}}},line:{{color:"{color}"}}}});')

    def text(t, x, y, w, h, size, color, bold=False, align="left", italic=False, valign="middle"):
        b = "true" if bold else "false"
        it = "true" if italic else "false"
        L.append(f'  slide.addText("{esc(t)}",{{x:{x},y:{y},w:{w},h:{h},fontSize:{size},color:"{color}",bold:{b},italic:{it},align:"{align}",valign:"{valign}",wrap:true,margin:0}});')

    def bullets(items, x, y, w, h, size, color):
        if not items:
            return
        arr = []
        for i, item in enumerate(items):
            br = "true" if i < len(items) - 1 else "false"
            arr.append(f'{{text:"{esc(str(item))}",options:{{bullet:true,breakLine:{br},fontSize:{size},color:"{color}"}}}}')
        L.append(f'  slide.addText([{",".join(arr)}],{{x:{x},y:{y},w:{w},h:{h},valign:"top",margin:[8,5,5,5]}});')

    def add_image(path, x, y, w, h):
        # Normalize image path for Node.js
        norm = path.replace("\\", "/")
        L.append(f'  slide.addImage({{path:"{norm}",x:{x},y:{y},w:{w},h:{h}}});')

    for idx, sl in enumerate(slides):
        stype = sl.get("type", "content")
        stitle = sl.get("title", "")
        img_path = images.get(idx)

        L.append(f"\n// Slide {idx+1}: {stype}")
        L.append("slide = pres.addSlide();")
        L.append(f'  slide.background = {{color:"{p["bg"]}"}};')

        if stype == "title":
            if img_path:
                add_image(img_path, 0, 0, 10, 5.625)
                shape(0, 0, 10, 5.625, p["dark"], 55)
            else:
                oval(5.5, -2, 8, 8, p["accent"], 82)
                oval(-2, 2, 5, 5, p["accent2"], 85)
            shape(0, 0, 10, 0.06, p["accent"])
            shape(0, 5.565, 10, 0.06, p["accent2"])
            shape(0.4, 1.2, 9.2, 3.2, p["dark"], 30)
            text(esc(stitle), 0.7, 1.5, 8.6, 1.8, 40, p["white"], bold=True)
            sub = esc(sl.get("subtitle", deck.get("subtitle", "")))
            if sub:
                text(sub, 0.7, 3.3, 8.6, 0.7, 17, p["muted"], italic=True)
            text("YouTube to Slides  |  AI-Powered", 0.5, 5.2, 9, 0.3, 9, p["muted"])

        elif stype == "section":
            if img_path:
                add_image(img_path, 0, 0, 10, 5.625)
                shape(0, 0, 10, 5.625, p["dark"], 62)
            else:
                shape(0, 0, 10, 5.625, p["accent"])
                oval(7, -1, 6, 6, p["accent2"], 78)
            shape(0, 0, 0.3, 5.625, p["accent2"])
            text(esc(stitle), 0.7, 1.5, 8.5, 1.6, 34, p["white"], bold=True)
            sub = sl.get("subtitle", "")
            if sub:
                text(esc(sub), 0.7, 3.3, 8.5, 0.8, 17, p["muted"])

        elif stype == "content":
            if img_path:
                add_image(img_path, 6.2, 0.9, 3.6, 4.5)
                shape(6.2, 0.9, 3.6, 4.5, p["dark"], 20)
                content_w = 5.8
            else:
                oval(7, 1, 4, 4, p["accent2"], 90)
                content_w = 9.0
            shape(0, 0, 10, 1.0, p["bg2"])
            shape(0, 0, 0.06, 1.0, p["accent"])
            text(esc(stitle), 0.35, 0.08, 9, 0.84, 24, p["text"], bold=True)
            shape(0.4, 1.08, 0.055, 4.35, p["accent"])
            bullets(sl.get("body", []), 0.65, 1.1, content_w - 0.8, 4.3, 15, p["text"])

        elif stype == "two_col":
            shape(0, 0, 10, 1.0, p["bg2"])
            text(esc(stitle), 0.4, 0.1, 9.2, 0.8, 22, p["text"], bold=True)
            shape(0.25, 1.1, 4.5, 4.35, p["card"])
            shape(0.25, 1.1, 4.5, 0.07, p["accent"])
            text(esc(sl.get("left_title", "Left")), 0.45, 1.2, 4.1, 0.55, 14, p["accent"], bold=True)
            bullets(sl.get("left_body", []), 0.45, 1.82, 4.1, 3.5, 13, p["text"])
            shape(5.25, 1.1, 4.5, 4.35, p["card"])
            shape(5.25, 1.1, 4.5, 0.07, p["accent2"])
            text(esc(sl.get("right_title", "Right")), 5.45, 1.2, 4.1, 0.55, 14, p["accent2"], bold=True)
            bullets(sl.get("right_body", []), 5.45, 1.82, 4.1, 3.5, 13, p["text"])

        elif stype == "stats":
            if img_path:
                add_image(img_path, 0, 0, 10, 5.625)
                shape(0, 0, 10, 5.625, p["dark"], 72)
            shape(0, 0, 10, 1.0, p["bg2"])
            text(esc(stitle), 0.4, 0.1, 9.2, 0.8, 24, p["text"], bold=True)
            stats = sl.get("stats", [])[:4]
            n = len(stats)
            if n:
                card_w = 9.2 / n
                for i, stat in enumerate(stats):
                    sx = 0.4 + i * card_w
                    shape(sx, 1.15, card_w - 0.2, 4.2, p["card"])
                    shape(sx, 1.15, card_w - 0.2, 0.07, p["accent"])
                    text(esc(stat.get("value", "")), sx+0.1, 1.7, card_w-0.4, 1.5, 38, p["accent"], bold=True, align="center")
                    text(esc(stat.get("label", "")), sx+0.1, 3.3, card_w-0.4, 1.8, 13, p["muted"], align="center")

        elif stype == "quote":
            if img_path:
                add_image(img_path, 0, 0, 10, 5.625)
                shape(0, 0, 10, 5.625, p["dark"], 68)
            else:
                oval(-1, -1, 6, 6, p["accent"], 88)
                oval(7, 3, 5, 5, p["accent2"], 90)
            text('\u201c', 0.5, 0.1, 3, 1.6, 90, p["accent"], bold=True)
            quote = esc(sl.get("quote", ""))
            author = esc(sl.get("quote_author", ""))
            shape(1.5, 1.2, 7, 2.8, p["dark"], 35)
            text(quote, 1.8, 1.3, 6.5, 2.6, 19, p["white"], italic=True, align="center", valign="middle")
            if author:
                shape(4.0, 4.2, 2, 0.055, p["accent"])
                text(f"\u2014 {author}", 1.5, 4.3, 7, 0.55, 13, p["muted"], align="center")

        elif stype == "image_focus":
            if img_path:
                add_image(img_path, 0, 0, 10, 5.625)
                shape(0, 0, 10, 5.625, p["dark"], 45)
            else:
                shape(0, 0, 10, 5.625, p["bg2"])
                oval(3, 0.5, 4, 4, p["accent"], 75)
            shape(0, 4.5, 10, 1.125, p["dark"], 50)
            text(esc(stitle), 0.5, 4.55, 9, 0.95, 24, p["white"], bold=True)
            body = sl.get("body", [])
            if body:
                shape(0.3, 0.8, 5.5, len(body) * 0.55 + 0.4, p["dark"], 50)
                bullets(body, 0.5, 0.9, 5.2, len(body) * 0.55 + 0.3, 14, p["white"])

        elif stype == "closing":
            if img_path:
                add_image(img_path, 0, 0, 10, 5.625)
                shape(0, 0, 10, 5.625, p["dark"], 60)
            else:
                oval(5, -1, 7, 7, p["accent"], 82)
                oval(-1.5, 2, 4, 4, p["accent2"], 85)
            shape(0, 0, 10, 0.07, p["accent"])
            shape(0, 5.555, 10, 0.07, p["accent2"])
            shape(0.4, 0.9, 9.2, 3.8, p["dark"], 35)
            text(esc(stitle), 0.7, 1.1, 8.5, 1.5, 34, p["white"], bold=True)
            sub = sl.get("subtitle", "")
            if sub:
                text(esc(sub), 0.7, 2.7, 8.5, 0.7, 15, p["muted"])
            body = sl.get("body", [])
            if body:
                bullets(body, 0.7, 3.5, 8.5, 1.8, 14, p["muted"])
            text("Generated by YT to Slides", 0.5, 5.22, 5, 0.28, 9, p["muted"])

        else:  # fallback content
            shape(0, 0, 10, 1.0, p["bg2"])
            text(esc(stitle), 0.4, 0.1, 9.2, 0.8, 24, p["text"], bold=True)
            shape(0.4, 1.08, 0.055, 4.35, p["accent"])
            bullets(sl.get("body", []), 0.65, 1.1, 9.0, 4.3, 15, p["text"])

        notes = sl.get("speaker_notes", "")
        if notes:
            L.append(f'  slide.addNotes("{esc(notes)}");')

    L.append(f'\npres.writeFile({{fileName:"{out_path}"}}).then(()=>console.log("OK")).catch(e=>{{console.error(String(e));process.exit(1);}});')
    return "\n".join(L)


def build_pptx(deck: dict, images: dict, node_modules_path: str) -> bytes:
    """Build PPTX and return bytes. Works on Windows, Mac, Linux."""

    # Use Python's tempfile for cross-platform temp directory
    tmp_dir = tempfile.gettempdir()
    out_path  = os.path.join(tmp_dir, "yt2ppt_output.pptx")
    script_path = os.path.join(tmp_dir, "yt2ppt_gen.js")

    script = build_script(deck, out_path, images, node_modules_path)

    # Write script with UTF-8 encoding (important on Windows)
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script)

    result = subprocess.run(
        ["node", script_path],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=os.path.dirname(node_modules_path),  # run from project folder
    )

    if result.returncode != 0:
        raise RuntimeError(f"PPTX generation failed:\n{result.stderr[:500]}")
    if not os.path.exists(out_path):
        raise RuntimeError("PPTX file was not created by Node.js")

    with open(out_path, "rb") as f:
        return f.read()

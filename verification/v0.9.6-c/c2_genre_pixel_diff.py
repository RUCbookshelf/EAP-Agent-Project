"""v0.9.6-C2 follow-up 2: pixel diff between before/after element screenshots.

Compares the timing/tools expander headers and the Genre selectbox captured
from the pre-fix and post-fix states at identical layout coordinates, and
reports the ink bounding box inside the 16x16 chevron box plus the total
difference pixels. Saves difference-overlay PNGs for manual review.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageChops

OUT = Path(r"A:\EAP Agent Project\writing-feedback-mvp\verification\v0.9.6-c")
THRESHOLD = 150


def ink_bbox(img, x, y, w, h):
    crop = img.crop((int(x), int(y), int(x + w), int(y + h)))
    mask = crop.point(lambda p: 255 if p < THRESHOLD else 0)
    bbox = mask.getbbox()
    if bbox is None:
        return None
    data = list(mask.getdata())
    count = sum(1 for p in data if p == 255)
    return {"bbox": tuple(int(v) for v in bbox), "w": bbox[2] - bbox[0], "h": bbox[3] - bbox[1], "ink_pixels": count}


def diff_stats(before, after, name, out_name):
    b = Image.open(before).convert("L")
    a = Image.open(after).convert("L")
    result = {"name": name, "before_size": b.size, "after_size": a.size}
    if b.size != a.size:
        result["error"] = "size mismatch"
        return result
    bm = b.point(lambda p: 255 if p < THRESHOLD else 0)
    am = a.point(lambda p: 255 if p < THRESHOLD else 0)
    bdata = list(bm.getdata())
    adata = list(am.getdata())
    diff_pixels = sum(1 for i in range(len(bdata)) if bdata[i] != adata[i])
    result["diff_pixels"] = diff_pixels
    result["diff_pct"] = round(100.0 * diff_pixels / (b.width * b.height), 3)
    result["before_ink"] = ink_bbox(b, 0, 0, b.width, b.height)
    result["after_ink"] = ink_bbox(a, 0, 0, a.width, a.height)
    overlay = Image.merge("RGB", (b, a, b))
    overlay.save(OUT / out_name)
    result["overlay"] = out_name
    return result


def main():
    before_rects = json.loads((OUT / "c2_genre_before_elements_rects.json").read_text(encoding="utf-8"))
    after_rects = json.loads((OUT / "c2_genre_after_elements_rects.json").read_text(encoding="utf-8"))
    results = {}
    for name in ("timing", "tools", "genre_selectbox"):
        suffix = "_expander" if name != "genre_selectbox" else ""
        results[name] = diff_stats(
            OUT / f"c2_genre_before_elements_{name}{suffix}.png",
            OUT / f"c2_genre_after_elements_{name}{suffix}.png",
            name,
            f"c2_genre_diff_{name}{suffix}.png",
        )
        if name in ("timing", "tools"):
            ae = after_rects[name]
            cx = ae["chevron"]["x"] - ae["expander"]["x"]
            cy = ae["chevron"]["y"] - ae["expander"]["y"]
            results[name]["chevron_local"] = [round(cx, 2), round(cy, 2)]
            results[name]["chevron_before_ink"] = ink_bbox(
                Image.open(OUT / f"c2_genre_before_elements_{name}_expander.png").convert("L"), cx, cy, 16, 16)
            results[name]["chevron_after_ink"] = ink_bbox(
                Image.open(OUT / f"c2_genre_after_elements_{name}_expander.png").convert("L"), cx, cy, 16, 16)
    print(json.dumps(results, indent=2, sort_keys=True))
    with open(OUT / "c2_genre_pixel_diff.json", "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(results, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
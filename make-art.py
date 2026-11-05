#!/usr/bin/env python3
"""Turns the Higgsfield originals in art-src/ into game files in art/:
scene pictures, Pepys cut-out, Pepys talking animation sheet, trimmed voice lines."""
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

root = Path(__file__).parent
src, out = root / "art-src", root / "art"
out.mkdir(exist_ok=True)
FF = "/opt/homebrew/opt/ffmpeg-full/bin/"
FPS = 24


def key(rgb):
    """Removes the flat green background by colour distance from the corner colour."""
    rgb = rgb.astype(float)
    corners = np.concatenate([rgb[:8, :8].reshape(-1, 3), rgb[:8, -8:].reshape(-1, 3), rgb[-8:, :8].reshape(-1, 3), rgb[-8:, -8:].reshape(-1, 3)])
    bg = np.median(corners, 0)
    d = np.sqrt(((rgb - bg) ** 2).sum(-1))
    alpha = np.clip((d - 38) / 45, 0, 1)
    g = rgb[..., 1]
    m = np.maximum(rgb[..., 0], rgb[..., 2])
    rgb[..., 1] = np.where((g > m) & (alpha < 1), m + (g - m) * .25, g)  # despill the fringe
    a = Image.fromarray((alpha * 255).astype("uint8")).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(.8))
    img = Image.fromarray(rgb.astype("uint8")).convert("RGBA")
    img.putalpha(a)
    return img, a


def scenes():
    crops = {"newlondon": (0, .13, 1, 1)}  # the model wrote a caption in the top-left corner
    for name in ("museum", "bakery", "houses", "river", "cheese", "gap", "newlondon", "street"):
        img = Image.open(src / f"{name}.png").convert("RGB")
        if name in crops:
            l, t, r, b = crops[name]
            img = img.crop((int(l * img.width), int(t * img.height), int(r * img.width), int(b * img.height)))
        img.thumbnail((1400, 1400), Image.LANCZOS)
        img.save(out / f"{name}.webp", quality=80, method=6)


def best_loop(frames):
    small = np.stack([np.asarray(Image.fromarray(f).resize((48, 48))) for f in frames[::2]]).astype(float)
    n = len(small)
    least = int(2.6 * FPS / 2)
    best, pair = 1e18, (0, n - 1)
    for a in range(0, n - least):
        for b in range(a + least, n):
            score = ((small[a] - small[b]) ** 2).mean() - (b - a) * .06
            if score < best:
                best, pair = score, (a, b)
    return pair[0] * 2, pair[1] * 2


def sheet(name, cols=6, rows=6, frame_h=440):
    clip = src / "video" / f"{name}.mp4"
    w, h = map(int, subprocess.run([FF + "ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(clip)], capture_output=True, text=True).stdout.strip().split(","))
    raw = subprocess.run([FF + "ffmpeg", "-v", "error", "-i", str(clip), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    frames = np.frombuffer(raw, "uint8").reshape(-1, h, w, 3)
    a, b = best_loop(frames)
    picks = np.linspace(a, b, cols * rows, endpoint=False).astype(int)
    keyed = [key(frames[i]) for i in picks]
    box = None
    for _, al in keyed:
        c = al.point(lambda v: 255 if v > 60 else 0).getbbox()
        box = c if box is None else (min(box[0], c[0]), min(box[1], c[1]), max(box[2], c[2]), max(box[3], c[3]))
    pad = 6
    scale = (frame_h - pad * 2) / (box[3] - box[1])
    cw, ch = round((box[2] - box[0]) * scale), round((box[3] - box[1]) * scale)
    fw, fh = cw + pad * 2, ch + pad * 2
    canvas = Image.new("RGBA", (fw * cols, fh * rows), (0, 0, 0, 0))
    for i, (img, _) in enumerate(keyed):
        small = img.crop(box).convert("RGBa").resize((cw, ch), Image.LANCZOS).convert("RGBA")
        canvas.paste(small, ((i % cols) * fw + pad, (i // cols) * fh + pad))
    canvas.save(out / f"s-{name}.webp", quality=84, alpha_quality=90, method=4)
    info = {"cols": cols, "rows": rows, "fw": fw, "fh": fh, "loop": round((b - a) / FPS, 2)}
    print(name, info, (out / f"s-{name}.webp").stat().st_size // 1024, "KB")
    return info


def voices():
    vo = out / "voice"
    vo.mkdir(exist_ok=True)
    for f in sorted((src / "voice").glob("*.wav")):
        trim = "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse,apad=pad_dur=0.15"
        subprocess.run([FF + "ffmpeg", "-v", "error", "-y", "-i", str(f), "-af", trim, "-ac", "1", "-b:a", "64k", str(vo / f"{f.stem}.mp3")], check=True)


scenes()
info = sheet("pepys")
(out / "sheets.json").write_text(json.dumps({"pepys": info}))
voices()

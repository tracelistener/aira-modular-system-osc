"""Module-menu page (PNL_SEL_SUB_R5.png) for the SYSTEM OSCILLATOR: new thumbnail + 'SYSTEM OSCILLATOR' caption
assembled from Roland's own caption glyphs on the same page. Offline image work only."""
import numpy as np
from PIL import Image

IMG = 'C:/Users/admin/AppData/Local/Roland/AIRA Modular Customizer/img'
CAP_Y0, CAP_Y1 = 1540, 1572          # single-line caption band, bottom row (2x page)


def knob_frame(sheet, k):
    h = sheet.height
    return sheet.crop((k * h, 0, (k + 1) * h, h))


def caption_alpha(a, x0, x1, y0=CAP_Y0, y1=CAP_Y1):
    lum = a[y0:y1, x0:x1, :3].mean(2)
    bgl = np.median(lum)
    peak = np.percentile(lum, 99.7)
    al = np.clip((lum - bgl) / (peak - bgl), 0, 1)
    al[al < 0.04] = 0
    return al, peak


def glyphs(al):
    on = (al > 0.12).any(0)
    runs, x = [], 0
    while x < len(on):
        if on[x]:
            s = x
            while x < len(on) and on[x]:
                x += 1
            runs.append((s, x))
        else:
            x += 1
    return runs


def build(page2x, page1x, panel2x):
    a = np.asarray(page2x.convert('RGBA')).astype(float)
    # --- source glyphs: SHORT DELAY (S, T, E, Y) and COMPRESSOR (M) from row 0; 'OSCILLATOR' from SAW OSCILLATOR.
    # Row-0 caption text starts at y=112 and row-3 text at y=1546 (same font and size), so glyphs keep their
    # vertical placement inside equal-height bands offset by 1434 px; only the horizontal extent is cropped.
    from scipy import ndimage
    B0, B3, BH = 104, 104 + 1434, 36
    def hcrop(al):
        cols = np.where((al > 0.12).any(0))[0]
        return al[:, cols[0]:cols[-1] + 1]
    def components(al):
        lab, n = ndimage.label(al > 0.12)
        out = []
        for k in range(1, n + 1):
            m = ndimage.binary_dilation(lab == k, iterations=2)
            xs = np.where(m.any(0))[0]
            out.append((xs.mean(), np.where(m, al, 0)))
        return [c for _, c in sorted(out, key=lambda t: t[0])]
    sd, _ = caption_alpha(a, 180, 350, B0, B0 + BH)
    sd_g = components(sd)          # S H O R T D E L A Y (connected components, so kerned A/Y separate)
    assert len(sd_g) == 10, len(sd_g)
    cp, _ = caption_alpha(a, 840, 1010, B0, B0 + BH)
    cp_g = components(cp)          # C O M P R E S S O R
    assert len(cp_g) == 10, len(cp_g)
    saw, peak = caption_alpha(a, 488, 700, B3, B3 + BH)
    runs = glyphs(saw)
    assert len(runs) == 11           # S, AW, O, S, C, I, L, L, AT, O, R (two kerned pairs)
    word2 = saw[:, runs[2][0]:runs[10][1]]                 # 'OSCILLATOR' exactly as Roland set it
    S, T, E, Y = (hcrop(sd_g[i]) for i in (0, 4, 6, 9))
    M = hcrop(cp_g[2])
    for gph in (S, T, E, Y, M):
        assert gph.shape[0] == BH
    gap = 3                          # SHORT DELAY letter gaps are 3 px (R-T 1 px, D-E 4 px)
    space = runs[2][0] - runs[1][1]  # word gap in 'SAW OSCILLATOR'
    parts = [S, gap, Y, gap, S, gap, T, gap, E, gap, M, space, word2]
    width = sum(p.shape[1] if hasattr(p, 'shape') else p for p in parts)
    top = B3
    # --- erase the old caption band (x 120..410, clear of the neighbouring captions) by per-row interpolation
    x0, x1 = 120, 410
    ya, yb = CAP_Y0 - 14, CAP_Y1 + 14
    for y in range(ya, yb):
        left = a[y, x0 - 12:x0, :3].mean(0)
        right = a[y, x1:x1 + 12, :3].mean(0)
        t = np.linspace(0, 1, x1 - x0)[:, None]
        a[y, x0:x1, :3] = left * (1 - t) + right * t
    # --- set the new caption centred on the column (x 264), same band and ink as Roland's captions
    colr = np.array([peak] * 3)
    x = int(round(264 - width / 2))
    assert x > x0 and x + width < x1
    for p in parts:
        if hasattr(p, 'shape'):
            h = p.shape[0]
            reg = a[top:top + h, x:x + p.shape[1], :3]
            a[top:top + h, x:x + p.shape[1], :3] = reg * (1 - p[..., None]) + colr * p[..., None]
            x += p.shape[1]
        else:
            x += p
    page = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')
    # --- thumbnail: the new panel with its knob sprites at their preset positions
    knobs = Image.open(IMG + '/2x/KNOB_L.png').convert('RGBA')
    thumb = panel2x.convert('RGBA').copy()
    thumb.alpha_composite(knob_frame(knobs, 21), (202, 88))    # RANGE 32' (value 2)
    thumb.alpha_composite(knob_frame(knobs, 16), (202, 268))   # WAVE position 0 (xClips[0] = 16)
    thumb.alpha_composite(knob_frame(knobs, 0), (48, 268))     # COLOR 0
    box = (188, 1608, 152, 348)
    small = thumb.resize((box[2], box[3]), Image.LANCZOS)
    base = page.crop((518, box[1], 518 + box[2], box[1] + box[3]))   # SAW thumbnail as clean base
    page.paste(base, (box[0], box[1]))
    page.alpha_composite(small, (box[0], box[1]))
    # --- 1x page: replace only the caption band and thumbnail with downscaled 2x regions
    p1 = page1x.convert('RGBA').copy()
    cap = page.crop((x0 - 8, ya, x1 + 8, yb)).resize(((x1 - x0 + 16) // 2, (yb - ya) // 2), Image.LANCZOS)
    p1.paste(cap, ((x0 - 8) // 2, ya // 2))
    th = page.crop((box[0] - 4, box[1] - 4, box[0] + box[2] + 4, box[1] + box[3] + 4)).resize(((box[2] + 8) // 2, (box[3] + 8) // 2), Image.LANCZOS)
    p1.paste(th, ((box[0] - 4) // 2, (box[1] - 4) // 2))
    return page, p1


if __name__ == '__main__':
    import sys
    panel = Image.open(sys.argv[1])
    p2, p1 = build(Image.open(IMG + '/2x/PNL_SEL_SUB_R5.png'), Image.open(IMG + '/1x/PNL_SEL_SUB_R5.png'), panel)
    p2.save('picker_2x_preview.png'); p1.save('picker_1x_preview.png')
    p2.crop((100, 1480, 760, 1990)).save('picker_crop.png')

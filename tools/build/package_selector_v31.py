"""Package the v3.1 selector (v3 jacks, lighter adapter, COLOR clamp, module-menu page) after the offline replay passes.
No device I/O and no Customizer install (install_customizer_v3.py is staged, not run).

outputs/wave-selector-v31-inputs/
  firmware/AIRA_MODULAR_UPD.BIN     v3 candidate (HARDWARE UNTESTED)
  rollback-v2/, rollback-v1/        the two earlier selector images
  presets/                          v1 presets unchanged, VOICE_S1M_CB (gate -> SYNC TRIG IN), VOICE_S1M_SYNC_DEMO
  customizer/, customizer-backup/   staged type-28 UI (CV IN, FINE IN, COLOR IN, SYNC TRIG IN) + current installed copies
"""
import re, shutil, zipfile, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from build_wave_selector_v31 import *
from picker import build as build_picker

APPDIR = Path('C:/Users/admin/AppData/Local/Roland/AIRA Modular Customizer')
FONT = 'C:/Windows/Fonts/bahnschrift.ttf'
ORANGE = np.array([218, 98, 12], float)
BG = np.array([245, 243, 240], float)
V2_OUT = ROOT / 'outputs/wave-selector-v2-cowbell'
COWBELL = ROOT / 'work/cowbell2'


def text_alpha(text, size, width_axis=87.5, weight=400):
    f = ImageFont.truetype(FONT, size)
    vals = []
    for ax in f.get_variation_axes():
        nm = ax['name'] if isinstance(ax['name'], str) else ax['name'].decode()
        vals.append(weight if nm.lower().startswith('weight') else width_axis if nm.lower().startswith('width') else ax['default'])
    f.set_variation_by_axes(vals)
    l, t, r, b = f.getbbox(text)
    im = Image.new('L', (r - l + 4, b - t + 4), 0)
    ImageDraw.Draw(im).text((2 - l, 2 - t), text, fill=255, font=f)
    m = np.array(im) / 255.0
    rows = np.where((m > 0.3).any(1))[0]
    return m[rows[0]:]


def paint(a, alpha, x, y, color=ORANGE):
    h, w = alpha.shape
    reg = a[y:y + h, x:x + w, :3]
    a[y:y + h, x:x + w, :3] = reg * (1 - alpha[..., None]) + color * alpha[..., None]


def teal_alpha(sub, teal):
    """Fraction of Roland's teal ink in a SAW-panel crop (colour cast only; greys and background -> 0)."""
    c = (sub[..., 1] + sub[..., 2]) / 2 - sub[..., 0]
    c0 = (BG[1] + BG[2]) / 2 - BG[0]
    ct = (teal[1] + teal[2]) / 2 - teal[0]
    return np.clip((c - c0) / (ct - c0), 0, 1)


def panel(cur2x, saw2x):
    a = np.asarray(Image.open(cur2x).convert('RGBA')).astype(float)
    s = np.asarray(Image.open(saw2x).convert('RGBA')).astype(float)
    assert a.shape[:2] == (874, 382) == s.shape[:2]
    ink = lambda arr, x0, y0, x1, y1: np.abs(arr[y0:y1, x0:x1, :3] - BG).sum(2) > 40
    # sanity: the v2 panel (installed) is what we edit: TRIG IN label present, new jack areas blank
    assert ink(a, 60, 550, 170, 592).any() and not ink(a, 60, 450, 170, 545).any() and not ink(a, 215, 450, 320, 545).any()
    # Roland's teal, from the SAW panel's SYNC TRIG IN label
    lab = s[74:106, 73:152, :3].reshape(-1, 3)
    teal = lab[np.argmax(((lab[:, 1] + lab[:, 2]) / 2 - lab[:, 0]))]
    # 1) erase v2's 'TRIG IN' label with clean background rows from the same columns just above it
    a[560:590, 60:170, :3] = a[530:560, 60:170, :3]
    assert not ink(a, 60, 550, 170, 592).any()
    # 2) COLOR IN and FINE IN sockets: Roland's socket art (the CV IN socket, 79,740 .. 146,810)
    sock = a[740:811, 79:147].copy()
    a[456:527, 79:147] = sock
    a[456:527, 234:302] = sock
    # 3) COLOR IN arrow: Roland's SAW-panel arrow (same COLOR knob position), recoloured orange
    arr = teal_alpha(s[398:457, 95:135, :3], teal)
    paint(a, arr, 95, 398)
    # 4) SYNC TRIG IN label: Roland's two-line SAW label, 45 px above the jack like on the SAW panel
    lab_a = teal_alpha(s[74:106, 73:152, :3], teal)
    paint(a, lab_a, 73, 597 - 45)
    # 5) FINE IN label in the same style as SYNC OUT, centred on its socket, in the strip under the WAVE knob
    ref = np.abs(a[556:592, 215:330, :3] - BG).sum(2) > 60
    rows = np.where(ref.any(1))[0]
    cap_h = rows[-1] - rows[0] + 1
    for size in range(12, 32):
        m = text_alpha('SYNC OUT', size)
        r = np.where((m > 0.3).any(1))[0]
        if r[-1] - r[0] + 1 >= cap_h:
            break
    m = text_alpha('FINE IN', size)
    x = int(round(267.5 - m.shape[1] / 2))
    y = 436
    assert y + m.shape[0] < 456 and not ink(a, x, y, x + m.shape[1], y + m.shape[0]).any()
    paint(a, m, x, y)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA'), dict(label_size=size, teal=[int(v) for v in teal])


def edit_js(text):
    start = text.index('\t28: {')
    end = text.index('\t29: {', start)
    block = text[start:end]
    m = re.search(r"\t\t\t\{ // in3: TRIG IN \(CB wave[^\n]*\n\t\t\t\tbase: 'jack\.in',\r?\n"
                  r"\t\t\t\tposition: UIPoint\.make\(79, 597\),\r?\n\t\t\t\tinput: 2,\r?\n\t\t\t\},(\r?\n)", block)
    assert m, 'v2 TRIG IN jack entry not found in the installed Customizer'
    nl = m.group(1)
    jack = lambda c, x, y, i: ('\t\t\t{ // ' + c + nl + "\t\t\t\tbase: 'jack.in'," + nl +
                               '\t\t\t\tposition: UIPoint.make(%d, %d),' % (x, y) + nl + '\t\t\t\tinput: %d,' % i + nl + '\t\t\t},' + nl)
    new = (jack('in2: FINE IN (selector v3: pitch + FINE/12, 1.0 = 1 semitone).', 234, 456, 1) +
           jack('in3: COLOR IN (selector v3: adds to COLOR, like the stock SAW).', 79, 456, 2) +
           jack('in4: SYNC TRIG IN (selector v3: rising edge through 0.3 hard-syncs the wave; strikes CB).', 79, 597, 3))
    block = block[:m.start()] + new + block[m.end():]
    assert block.count("base: 'jack.in'") == 4
    return text[:start] + block + text[end:]


def presets():
    from aira_preset import make_preset
    cb2 = (V2_OUT / 'presets/VOICE_S1M_CB.bin').read_bytes()
    cb3 = bytearray(cb2)
    mat = 120
    assert cb3[mat + 17 * 42 + 12] != 0 and cb3[mat + 17 * 42 + 13] == 0
    cb3[mat + 17 * 42 + 13] = cb3[mat + 17 * 42 + 12]      # MIDINOTE gate -> SYSTEM in4 (SYNC TRIG IN)
    cb3[mat + 17 * 42 + 12] = 0                             # (in3 is COLOR IN now)
    tri = (ROOT / 'outputs/wave-selector-v1/presets/VOICE_SYSTEM_TRI.bin').read_bytes()
    main = list(tri[40:56])
    slots = {1: [31, 3, 12, 0, 0],       # MIDINOTE
             2: [29, 1, 50, 0, 50],      # stock SAW = sync master (its FINE knob sweeps the sync)
             3: [28, 2, 2, 0, 100],      # SYSTEM OSC, WAVE 2 = TRI (slave)
             4: [2, 2, 60, 70, 25],      # ADSR (as VOICE_SYSTEM_TRI)
             5: [9, 0, 0, 50, 50],       # AMP  (as VOICE_SYSTEM_TRI)
             6: [10, 100, 10, 0, 0]}     # MIXER: CV x1.0 + ADSR x0.1 (= +1 octave sweep on the slave)
    routes = [(10, 14, 2), (10, 30, 2),  # MIDINOTE CV -> SAW CV IN, MIXER in1
              (11, 22, 3),               # gate -> ADSR
              (16, 28, 4), (16, 29, 4), (16, 31, 4),   # ADSR -> AMP CV, MIXER in2
              (20, 18, 2),               # MIXER -> SYSTEM CV IN
              (12, 21, 1),               # SAW OUT -> SYSTEM SYNC TRIG IN
              (14, 26, 5), (14, 27, 5),  # SYSTEM OUT -> AMP
              (18, 0, 6), (19, 1, 6)]    # AMP -> main
    demo = make_preset(slots, routes, main=main)
    return bytes(cb3), demo, dict(slots=slots, routes=routes)


def package():
    app, fw, meta = build()
    from verify_wave_selector_v31 import verify
    meta['verification'] = verify()
    image = pack_application(fw, app)
    decoded, record = unpack_record(image, APP_RECORD, APP_END)
    assert decoded == app and pack_application(fw, decoded) == image
    v2fw, v1fw = V2_FW.read_bytes(), V1_FW.read_bytes()
    assert sha(v2fw) == V2_FW_SHA and sha(v1fw) == V1_FW_SHA
    meta.update(status='OFFLINE CHECKS PASSED; HARDWARE UNTESTED', firmware_sha256=sha(image), record=record,
                outer=validate_outer(image, fw))
    for d in ['firmware', 'rollback-v2', 'rollback-v1', 'presets', 'evidence', 'source', 'customizer/js', 'customizer/img/1x',
              'customizer/img/2x', 'customizer-backup/js', 'customizer-backup/img/1x', 'customizer-backup/img/2x']:
        (OUT / d).mkdir(parents=True, exist_ok=True)
    (OUT / 'firmware/AIRA_MODULAR_UPD.BIN').write_bytes(image)
    (OUT / 'rollback-v2/AIRA_MODULAR_UPD.BIN').write_bytes(v2fw)
    (OUT / 'rollback-v1/AIRA_MODULAR_UPD.BIN').write_bytes(v1fw)
    plist = []
    for p in sorted((ROOT / 'outputs/wave-selector-v1/presets').glob('*.bin')):
        shutil.copy2(p, OUT / 'presets' / p.name)
        plist.append(dict(file=p.name, source='v1 (unchanged)', sha256=sha(p.read_bytes())))
    cb3, demo, spec = presets()
    (OUT / 'presets/VOICE_S1M_CB.bin').write_bytes(cb3)
    (OUT / 'presets/VOICE_S1M_SYNC_DEMO.bin').write_bytes(demo)
    plist += [dict(file='VOICE_S1M_CB.bin', source='v2 preset, gate moved from in3 to in4 (SYNC TRIG IN)', sha256=sha(cb3)),
              dict(file='VOICE_S1M_SYNC_DEMO.bin', source='new', sha256=sha(demo), spec=spec)]
    (OUT / 'presets/VALIDATION.json').write_text(json.dumps(plist, indent=2, default=str))
    files = ['js/ui_module_configs.js', 'img/1x/PNL_OSCTRI.png', 'img/2x/PNL_OSCTRI.png',
             'img/1x/PNL_SEL_SUB_R5.png', 'img/2x/PNL_SEL_SUB_R5.png', '150.zip']
    for rel in files:
        shutil.copy2(APPDIR / rel, OUT / 'customizer-backup' / rel)
    text = (APPDIR / 'js/ui_module_configs.js').read_bytes().decode('utf-8')
    (OUT / 'customizer/js/ui_module_configs.js').write_bytes(edit_js(text).encode('utf-8'))
    img, pmeta = panel(APPDIR / 'img/2x/PNL_OSCTRI.png', APPDIR / 'img/2x/PNL_OSCSAW.png')
    img.save(OUT / 'customizer/img/2x/PNL_OSCTRI.png')
    img.resize((191, 437), Image.Resampling.LANCZOS).save(OUT / 'customizer/img/1x/PNL_OSCTRI.png')
    pk2, pk1 = build_picker(Image.open(APPDIR / 'img/2x/PNL_SEL_SUB_R5.png'), Image.open(APPDIR / 'img/1x/PNL_SEL_SUB_R5.png'), img)
    pk2.save(OUT / 'customizer/img/2x/PNL_SEL_SUB_R5.png')
    pk1.save(OUT / 'customizer/img/1x/PNL_SEL_SUB_R5.png')
    overlays = {'js/ui_module_configs.js': (OUT / 'customizer/js/ui_module_configs.js').read_bytes(),
                'js/ui_module_data.js': (APPDIR / 'js/ui_module_data.js').read_bytes()}
    overlays.update({f'img/{s}/{n}': (OUT / f'customizer/img/{s}/{n}').read_bytes() for s in ('1x', '2x')
                     for n in ('PNL_OSCTRI.png', 'PNL_SEL_SUB_R5.png')})
    assert b'sendPatchSafely' in overlays['js/ui_module_data.js']
    with zipfile.ZipFile(APPDIR / '150.zip') as zin, zipfile.ZipFile(OUT / 'customizer/150.zip', 'w') as zout:
        matched = set()
        for info in zin.infolist():
            key = next((k for k in overlays if info.filename == k or info.filename.endswith('/' + k)), None)
            zout.writestr(info, overlays[key] if key else zin.read(info.filename))
            if key:
                matched.add(key)
        for key in set(overlays) - matched:
            assert key.startswith('img/') and (key.endswith('/PNL_OSCTRI.png') or key.endswith('/PNL_SEL_SUB_R5.png'))
            zout.writestr(key, overlays[key], compress_type=zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(OUT / 'customizer/150.zip') as z:
        assert z.testzip() is None
    inst = (V2_OUT / 'install_customizer_v2.py').read_text().replace('_backup_before_wave_selector_v2_', '_backup_before_wave_selector_v31_')
    inst = inst.replace('staged v2 Customizer assets (WAVE 0..6 incl. CB, TRIG IN jack)',
                        'staged v3.1 Customizer assets (CV IN, FINE IN, COLOR IN, SYNC TRIG IN; SYSTEM OSCILLATOR in the module menu)')
    inst = inst.replace('install_customizer_v2.py', 'install_customizer_v31.py')
    old_files = "FILES = ['js/ui_module_configs.js', 'img/1x/PNL_OSCTRI.png', 'img/2x/PNL_OSCTRI.png', '150.zip']"
    assert old_files in inst
    inst = inst.replace(old_files, "FILES = ['js/ui_module_configs.js', 'img/1x/PNL_OSCTRI.png', 'img/2x/PNL_OSCTRI.png',\n"
                                   "         'img/1x/PNL_SEL_SUB_R5.png', 'img/2x/PNL_SEL_SUB_R5.png', '150.zip']")
    (OUT / 'install_customizer_v31.py').write_text(inst)
    shutil.copy2(HERE / 'verification.json', OUT / 'evidence/selector-verification.json')
    shutil.copy2(HERE / 'build.json', OUT / 'evidence/build.json')
    for pth in list(HERE.iterdir()) + [COWBELL / n for n in ('system_osc_v3.py', 'system_osc_v31.py', 'cowbell_program.py', 'cb_model.py', 'isa.py', 'esc.py')]:
        if pth.suffix in ('.py', '.s', '.txt'):
            shutil.copy2(pth, OUT / 'source' / pth.name)
    meta['presets'] = plist
    meta['panel'] = pmeta
    meta['customizer_installed'] = False
    (OUT / 'MANIFEST.json').write_text(json.dumps(meta, indent=2, default=str) + '\n')
    print('PACKAGED', sha(image))
    return meta


if __name__ == '__main__':
    package()

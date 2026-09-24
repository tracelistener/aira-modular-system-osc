"""Install the SYSTEM OSCILLATOR files into the Roland AIRA Modular Customizer (Windows).

    python install_customizer.py                   install (close the Customizer first)
    python install_customizer.py --restore DIR     put back the files saved in backup folder DIR
    python install_customizer.py --app PATH        use a Customizer folder other than %LOCALAPPDATA%\\Roland\\AIRA Modular Customizer

What it changes: the type-28 module entry (FORMANT FILTER -> SYSTEM OSCILLATOR), its panel, the module-menu page, and
safe patch loading (the Customizer empties the unit before sending a patch, which avoids DSP-overload hangs).
The same six files are updated inside the Customizer's 150.zip. Everything replaced is backed up first, and the
install refuses to run on a Customizer version it doesn't recognise. Standard library only; no network or device I/O.
"""
import datetime, hashlib, json, os, shutil, sys, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = ['js/ui_module_configs.js', 'js/ui_module_data.js', 'img/1x/PNL_OSCTRI.png', 'img/2x/PNL_OSCTRI.png',
         'img/1x/PNL_SEL_SUB_R5.png', 'img/2x/PNL_SEL_SUB_R5.png']
KNOWN = {
    "js/ui_module_configs.js": [
        "386ce22b056a0b95e9d22b9f4bd8a3f298231b0aeeb28054c011be65497efe0d",
        "414e5480e5b4979617dca81d02128e8f94609965f8ff128e8aeb2d4fe94dea66",
        "4b7e2f3465b72ee0cb09dd55c388454e373c93defaaf8df5d6d8e97a14b58716",
        "62aae2b04cd8aab8fc5b0c119822513c7f32651bc4eafbfde98e3be8811b9eea",
        "68c1cb1a4bac5e82496e0f9824992bdbc3b163f52b4608bf46fd161c1aadc09b",
        "a44d1e4fc865cbc359619a088bd12de417bded906704a907ec01d5094fa57482",
        "b157c3fa12f56411e44cbf76d2f7965355820d8a9ee7d250d59cf3621d6b6553"
    ],
    "js/ui_module_data.js": [
        "500fadd559512137f71096af5ca64b18c0df987476ab34ce880c6dabf68e977b",
        "809f510a76122eb86715374c2d4d9b857e63cd9741c8cd912b62f83963db185a"
    ]
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def patch_zip(app, overlays):
    src, tmp = app / '150.zip', app / '150.zip.tmp'
    matched = set()
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(tmp, 'w') as zout:
        for info in zin.infolist():
            key = next((k for k in overlays if info.filename == k or info.filename.endswith('/' + k)), None)
            zout.writestr(info, overlays[key] if key else zin.read(info.filename))
            if key:
                matched.add(key)
        for key in sorted(set(overlays) - matched):
            zout.writestr(key, overlays[key], compress_type=zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(tmp) as z:
        assert z.testzip() is None
        names = z.namelist()
        for key, data in overlays.items():
            hit = [n for n in names if n == key or n.endswith('/' + key)]
            assert hit and all(z.read(n) == data for n in hit), key
    os.replace(tmp, src)


def restore(app, backup):
    receipt = json.loads((backup / 'backup.json').read_text())
    for rel in receipt['existed']:
        shutil.copy2(backup / rel, app / rel)
    for rel in receipt['absent']:
        if (app / rel).exists():
            (app / rel).unlink()
    print('restored from', backup)


def install(app):
    for rel in KNOWN:
        cur = sha(app / rel)
        if cur not in KNOWN[rel]:
            sys.exit('Unrecognised %s (sha256 %s). This Customizer version was not tested; nothing was changed.' % (rel, cur))
    backup = app / ('_backup_before_system_osc_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    existed, absent = [], []
    for rel in FILES + ['150.zip']:
        if (app / rel).exists():
            (backup / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(app / rel, backup / rel)
            assert sha(backup / rel) == sha(app / rel)
            existed.append(rel)
        else:
            absent.append(rel)
    (backup / 'backup.json').write_text(json.dumps(dict(existed=existed, absent=absent), indent=2))
    try:
        for rel in FILES:
            (app / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(HERE / 'files' / rel, app / rel)
            assert sha(app / rel) == sha(HERE / 'files' / rel)
        patch_zip(app, {rel: (HERE / 'files' / rel).read_bytes() for rel in FILES})
    except Exception:
        restore(app, backup)
        raise
    print('Installed. Backup:', backup)
    print('To undo: python install_customizer.py --restore "%s"' % backup)


if __name__ == '__main__':
    args = sys.argv[1:]
    app = Path(os.environ.get('LOCALAPPDATA', '')) / 'Roland' / 'AIRA Modular Customizer'
    if '--app' in args:
        app = Path(args[args.index('--app') + 1])
    if not (app / '150.zip').exists():
        sys.exit('Customizer not found at %s (use --app PATH)' % app)
    if '--restore' in args:
        restore(app, Path(args[args.index('--restore') + 1]))
    else:
        install(app)

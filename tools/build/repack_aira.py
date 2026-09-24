"""Repackage an existing oscillator application, without changing its code.

Qualified for AIRA Modular v1.05 build 0493. Source firmware is read-only.
This script creates offline artifacts only and has no device/USB/flash access.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

from aira_lzss import compress_lzss
from decompress_aira_application import decompress_lzss

STOCK_SHA = "077e60f353a022e26ada6c24afdf7897f3953071ca5e745cf485b1507a9afdc3"
APP_RECORD, APP_HEADER, APP_START, APP_END = 0x40000, 0x40028, 0x40040, 0x140000
IMAGE_END, FILE_SIZE = 0x200000, 0x200010
APP_BASE = 0x60000000


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def unpack_record(image: bytes, offset: int, limit: int) -> tuple[bytes, dict]:
    require(offset + 0x40 <= len(image), "record header is truncated")
    load, delta, stored, checksum, entry, size = struct.unpack_from(
        "<6I", image, offset + 0x28)
    require(delta == 0x40, "unexpected record payload delta")
    require(0 < size <= 0x100000, "unsupported expanded record size")
    start, end = offset + delta, offset + delta + stored
    require(stored > 0 and end <= limit <= len(image), "record exceeds allocation")
    packed = image[start:end]
    require((sum(packed) & 0xFFFFFFFF) == checksum, "stored payload checksum mismatch")
    raw, consumed = decompress_lzss(packed, size)
    require(consumed == stored and len(raw) == size, "inexact LZSS consumption")
    require(image[end:limit] == b"\xff" * (limit - end), "unexpected non-padding data")
    return raw, dict(record_offset=offset, load=load, delta=delta, stored=stored,
                     checksum=checksum, entry=entry, expanded=size,
                     payload_end=end, application_sha256=sha(raw))


def validate_outer(image: bytes, template: bytes) -> dict:
    """Check the qualified ESC9 envelope and unchanged boot/updater regions.

    This is structural/template validation, not a claim of on-device execution.
    The exact official boot envelope is retained, including opaque fields.
    """
    require(len(image) == len(template) == FILE_SIZE, "unexpected complete image size")
    require(image[:12] == b"ESC91.000\0\0\0", "unexpected ESC9 signature")
    require(struct.unpack_from("<I", image, 0x10)[0] == IMAGE_END,
            "unexpected ESC9 image span")
    trailer = struct.unpack_from("<4I", image, IMAGE_END)
    require(trailer == (0x40, 0x13F, 0x1000, IMAGE_END), "unexpected update trailer")
    first_sector, last_sector, sector_bytes, declared_size = trailer
    require(declared_size == len(image) - 16 and sector_bytes > 0
            and first_sector <= last_sector, "invalid updater trailer")
    write_start = first_sector * sector_bytes
    write_end = (last_sector + 1) * sector_bytes
    require((write_start, write_end) == (APP_RECORD, APP_END),
            "update span includes non-application sectors")
    require(image[:0x40030] == template[:0x40030], "boot/updater or record prefix changed")
    require(image[0x40038:APP_START] == template[0x40038:APP_START],
            "application entry or expanded length changed")
    require(image[APP_END:] == template[APP_END:], "non-application region changed")
    require(image[APP_RECORD:APP_RECORD + 16] == b"AIRA-FX:Appli   ",
            "unexpected application record name")
    # The actual updater validates both inner records after the sector write.
    # The updater itself remains the byte-identical original region.
    _, updater = unpack_record(image, 0x2000, APP_RECORD)
    fields = {f"0x{x:02x}": f"0x{struct.unpack_from('<I', image, x)[0]:08x}"
              for x in (0x0C, 0x10, 0x14, 0x18, 0x1C, 0x20, 0x24, 0x28)}
    return dict(signature="ESC91.000", file_size=len(image),
                image_span=IMAGE_END, fields=fields, trailer=list(trailer),
                update_write_range_half_open=[write_start, write_end],
                updater_payload_checksum_verified=True,
                updater_application_sha256=updater["application_sha256"],
                original_boot_updater_preserved=True,
                original_non_application_region_preserved=True)


def pack_application(template: bytes, application: bytes) -> bytes:
    original, metadata = unpack_record(template, APP_RECORD, APP_END)
    require(len(application) == len(original), "expanded application length changed")
    require(metadata["load"] == metadata["entry"] == APP_BASE,
            "unexpected application load/entry")
    encoded = compress_lzss(application)
    require(APP_START + len(encoded) <= APP_END, "compressed application exceeds allocation")
    decoded, consumed = decompress_lzss(encoded, len(application))
    require(decoded == application and consumed == len(encoded), "encoder round-trip failed")
    image = bytearray(template)
    struct.pack_into("<II", image, 0x40030, len(encoded), sum(encoded) & 0xFFFFFFFF)
    image[APP_START:APP_END] = encoded + b"\xff" * (APP_END - APP_START - len(encoded))
    image = bytes(image)
    validate_outer(image, template)
    result, _ = unpack_record(image, APP_RECORD, APP_END)
    require(result == application, "packaged application differs")
    return image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stock", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path,
                        help="existing literal-only oscillator image")
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    stock, old = args.stock.read_bytes(), args.candidate.read_bytes()
    require(sha(stock) == STOCK_SHA, "stock image is not the qualified build 0493")
    require(args.output_dir.resolve() not in (args.stock.parent.resolve(),
                                            args.candidate.parent.resolve()),
            "use a separate output directory to preserve source files")
    validate_outer(stock, stock)
    validate_outer(old, stock)
    raw_stock, stock_meta = unpack_record(stock, APP_RECORD, APP_END)
    raw_candidate, old_meta = unpack_record(old, APP_RECORD, APP_END)
    # An unchanged application must recreate the entire official file exactly.
    require(pack_application(stock, raw_stock) == stock, "official full-image round-trip failed")
    rebuilt = pack_application(stock, raw_candidate)
    unpacked, new_meta = unpack_record(rebuilt, APP_RECORD, APP_END)
    require(unpacked == raw_candidate, "oscillator application changed")
    require(pack_application(stock, unpacked) == rebuilt, "rebuilt full-image round-trip failed")
    outer = validate_outer(rebuilt, stock)
    manifest = dict(status="PACKAGING VERIFIED OFFLINE; HARDWARE UNTESTED; NOT FLASHED",
                    source_stock=str(args.stock.resolve()), source_candidate=str(args.candidate.resolve()),
                    source_stock_sha256=sha(stock), source_candidate_sha256=sha(old),
                    candidate_sha256=sha(rebuilt), rollback_sha256=sha(stock),
                    patched_application_sha256=sha(raw_candidate),
                    stock=stock_meta, previous=old_meta, rebuilt=new_meta, outer=outer,
                    checks=dict(official_full_image_byte_identical_round_trip=True,
                                rebuilt_full_image_byte_identical_round_trip=True,
                                existing_oscillator_application_byte_identical=True,
                                stored_payload_checksum=True,
                                exact_lzss_consumption=True,
                                source_files_preserved=True),
                    limits=["Offline container validation does not prove hardware installation or audio output.",
                            "Exact bit meanings of boot-ROM header words 0x14, 0x1c, 0x20, 0x24, 0x28 remain unproven; preserved byte for byte."])
    args.output_dir.mkdir(parents=True, exist_ok=True)
    targets = [args.output_dir / name for name in
               ("AIRA_MODULAR_UPD.BIN", "ROLLBACK-AIRA_MODULAR_UPD.BIN", "MANIFEST.json")]
    require(not any(p.exists() for p in targets), "output files already exist; choose a new directory")
    targets[0].write_bytes(rebuilt)
    targets[1].write_bytes(stock)
    targets[2].write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(status=manifest["status"], previous_packed=old_meta["stored"],
                          rebuilt_packed=new_meta["stored"],
                          candidate_sha256=sha(rebuilt),
                          patched_application_sha256=sha(raw_candidate)), indent=2))


if __name__ == "__main__":
    main()

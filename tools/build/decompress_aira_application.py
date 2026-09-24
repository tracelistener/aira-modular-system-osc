"""Decompress a Roland AIRA Modular application record offline.

The algorithm is transcribed from the updater's Thumb routine at 0x01000C0A:
a 4096-byte LZSS ring initialized to zero, starting at position 0xFEE.
This tool validates the stored byte-sum and never modifies the source image.
Its output is an analysis artifact, not an update file.
"""

from __future__ import annotations

import argparse
import hashlib
import struct
from pathlib import Path


APP_RECORD = 0x40000
APP_HEADER = 0x40028


def decompress_lzss(source: bytes, output_size: int) -> tuple[bytes, int]:
    ring = bytearray(0x1000)
    ring_pos = 0xFEE
    source_pos = 0
    flags = 0
    output = bytearray()

    def get_byte() -> int:
        nonlocal source_pos
        if source_pos >= len(source):
            raise ValueError("compressed payload ended before requested output size")
        value = source[source_pos]
        source_pos += 1
        return value

    while len(output) < output_size:
        flags >>= 1
        if flags & 0x100 == 0:
            flags = get_byte() | 0xFF00

        if flags & 1:
            value = get_byte()
            output.append(value)
            ring[ring_pos] = value
            ring_pos = (ring_pos + 1) & 0xFFF
        else:
            low = get_byte()
            high_length = get_byte()
            back_pos = low | ((high_length & 0xF0) << 4)
            count = (high_length & 0x0F) + 3
            for index in range(count):
                if len(output) >= output_size:
                    break
                value = ring[(back_pos + index) & 0xFFF]
                output.append(value)
                ring[ring_pos] = value
                ring_pos = (ring_pos + 1) & 0xFFF

    return bytes(output), source_pos


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("firmware", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    image = args.firmware.read_bytes()
    load, delta, stored_size, checksum, entry, output_size = struct.unpack_from(
        "<6I", image, APP_HEADER
    )
    source_start = APP_RECORD + delta
    source = image[source_start : source_start + stored_size]
    if len(source) != stored_size:
        raise SystemExit("application payload is truncated")
    if sum(source) & 0xFFFFFFFF != checksum:
        raise SystemExit("stored payload byte-sum does not match header")

    output, consumed = decompress_lzss(source, output_size)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(output)

    print(f"load address:       0x{load:08X}")
    print(f"entry address:      0x{entry:08X}")
    print(f"compressed size:    0x{stored_size:X}")
    print(f"decompressed size:  0x{len(output):X}")
    print(f"source consumed:    0x{consumed:X}")
    print(f"source remainder:   0x{len(source)-consumed:X}")
    print(f"output SHA-256:     {hashlib.sha256(output).hexdigest().upper()}")
    print(f"output prefix:      {output[:24].hex(' ')}")
    print(f"analysis output:    {args.output.resolve()}")


if __name__ == "__main__":
    main()

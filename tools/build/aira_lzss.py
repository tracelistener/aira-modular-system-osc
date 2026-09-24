"""AIRA 4 KiB LZSS encoder; no firmware or hardware access.

Wire format is derived from decompress_aira_application.py:
  * zero-filled 4096-byte ring, initial write index 0xFEE;
  * flag bits LSB first, 1=one literal, 0=two-byte match;
  * match index = low | ((high_length & 0xF0) << 4);
  * match length = (high_length & 0x0F) + 3 (3..18 bytes).

The binary search tree chooses longest matches with deterministic tie breaking.
This implements the traditional N=4096/F=18 LZSS encoder structure. Whether its
choices equal Roland's encoder is measured separately against official streams.
The format has no EOF token: the container carries the expanded byte count.
"""
from __future__ import annotations

import argparse
from pathlib import Path

N, F, THRESHOLD = 4096, 18, 2
NIL = N


def compress_lzss(source: bytes) -> bytes:
    """Return a deterministic stream accepted by the existing AIRA decoder."""
    source = bytes(source)
    if not source:
        return b""
    text = bytearray(N + F - 1)
    left = [NIL] * (N + 1)
    right = [NIL] * (N + 257)
    parent = [NIL] * (N + 1)
    match_pos = match_len = 0

    def insert(r: int) -> None:
        nonlocal match_pos, match_len
        cmp = 1
        p = N + 1 + text[r]
        left[r] = right[r] = NIL
        match_len = 0
        while True:
            if cmp >= 0:
                if right[p] != NIL:
                    p = right[p]
                else:
                    right[p] = r
                    parent[r] = p
                    return
            else:
                if left[p] != NIL:
                    p = left[p]
                else:
                    left[p] = r
                    parent[r] = p
                    return
            i = 1
            while i < F:
                cmp = text[r + i] - text[p + i]
                if cmp:
                    break
                i += 1
            if i > match_len:
                match_pos, match_len = p, i
                if i == F:
                    break
        parent[r] = parent[p]
        left[r], right[r] = left[p], right[p]
        parent[left[p]] = r
        parent[right[p]] = r
        if right[parent[p]] == p:
            right[parent[p]] = r
        else:
            left[parent[p]] = r
        parent[p] = NIL

    def delete(p: int) -> None:
        if parent[p] == NIL:
            return
        if right[p] == NIL:
            q = left[p]
        elif left[p] == NIL:
            q = right[p]
        else:
            q = left[p]
            if right[q] != NIL:
                while right[q] != NIL:
                    q = right[q]
                right[parent[q]] = left[q]
                parent[left[q]] = parent[q]
                left[q] = left[p]
                parent[left[p]] = q
            right[q] = right[p]
            parent[right[p]] = q
        parent[q] = parent[p]
        if right[parent[p]] == p:
            right[parent[p]] = q
        else:
            left[parent[p]] = q
        parent[p] = NIL

    s, r = 0, N - F
    length = min(F, len(source))
    text[r:r + length] = source[:length]
    source_pos = length
    for i in range(1, F + 1):
        insert(r - i)
    insert(r)

    encoded = bytearray()
    group = bytearray([0])
    mask = 1
    while length:
        match_len = min(match_len, length)
        if match_len <= THRESHOLD:
            match_len = 1
            group[0] |= mask
            group.append(text[r])
        else:
            group.extend((match_pos & 0xFF,
                          ((match_pos >> 4) & 0xF0) | (match_len - 3)))
        mask <<= 1
        if mask == 0x100:
            encoded.extend(group)
            group = bytearray([0])
            mask = 1

        last_match_len = match_len
        read = 0
        while read < last_match_len and source_pos < len(source):
            value = source[source_pos]
            source_pos += 1
            delete(s)
            text[s] = value
            if s < F - 1:
                text[s + N] = value
            s = (s + 1) & (N - 1)
            r = (r + 1) & (N - 1)
            insert(r)
            read += 1
        while read < last_match_len:
            delete(s)
            s = (s + 1) & (N - 1)
            r = (r + 1) & (N - 1)
            length -= 1
            if length:
                insert(r)
            read += 1
    if len(group) > 1:
        encoded.extend(group)
    return bytes(encoded)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    from decompress_aira_application import decompress_lzss
    raw = args.source.read_bytes()
    encoded = compress_lzss(raw)
    decoded, consumed = decompress_lzss(encoded, len(raw))
    if decoded != raw or consumed != len(encoded):
        raise ValueError("LZSS round-trip failed; output not written")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(encoded)
    print(f"{len(raw):,} -> {len(encoded):,} bytes; exact round-trip verified")


if __name__ == "__main__":
    main()

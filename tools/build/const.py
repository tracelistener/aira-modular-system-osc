def c32(hi, lo):
    v = (hi << 16) | lo
    s = -1 if v >> 31 else 1
    e = (v >> 29) & 3
    m = v & 0x1fffffff
    return s * m * 2.0 ** (4 * e - 32)
def c24(v):
    s = -1 if (v >> 23) & 1 else 1
    e = (v >> 21) & 3
    m = v & 0x1fffff
    return s * m * 2.0 ** (4 * e - 24)

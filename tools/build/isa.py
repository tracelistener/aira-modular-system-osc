"""ESC2 record layout: header = [flags][len:5]; number of micro-op words m from the header's leading bit."""
def nmicro(H):
    if H & 0x8000:
        return 5 + ((H >> 6) & 3)
    for b, m in ((0x4000, 4), (0x2000, 3), (0x1000, 2), (0x0800, 1)):
        if H & b:
            return m
    return 0

def is_move(x):
    return (x & 0x0fe1) == 0x0fe0 and (x & 0x0fff) >= 0xfe0

def split(r):
    m = nmicro(r[0])
    return r[1:1 + m], r[1 + m:]

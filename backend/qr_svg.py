"""
qr_svg.py — Zero-dependency ISO/IEC 18004 QR Code SVG Generator (Versions 1–10, ECC Level L, Byte Mode).
Renders crisp, phone-camera-scannable SVG QR matrices for Axon IoT APK & Gateway pairing URLs.
"""

from typing import List, Tuple

# (total_codewords, ec_codewords_per_block, num_blocks_group1, data_per_block_g1, num_blocks_g2, data_per_block_g2, align_centers)
_QR_L_SPEC = {
    1:  (26,   7,  1, 19,  0, 0,  []),
    2:  (44,   10, 1, 34,  0, 0,  [6, 18]),
    3:  (70,   15, 1, 55,  0, 0,  [6, 22]),
    4:  (100,  20, 1, 80,  0, 0,  [6, 26]),
    5:  (134,  26, 1, 108, 0, 0,  [6, 30]),
    6:  (172,  18, 2, 68,  0, 0,  [6, 34]),
    7:  (196,  20, 2, 78,  0, 0,  [6, 22, 38]),
    8:  (242,  24, 2, 97,  0, 0,  [6, 24, 42]),
    9:  (292,  30, 2, 116, 0, 0,  [6, 26, 46]),
    10: (346,  18, 2, 68,  2, 69, [6, 28, 50]),
}

_GF_EXP = [0] * 512
_GF_LOG = [0] * 256
_x = 1
for _i in range(255):
    _GF_EXP[_i] = _x
    _GF_LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    _GF_EXP[_i] = _GF_EXP[_i - 255]


def _gf_mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return _GF_EXP[_GF_LOG[a] + _GF_LOG[b]]


def _rs_generator(degree: int) -> List[int]:
    poly = [1]
    for i in range(degree):
        nxt = [0] * (len(poly) + 1)
        factor = _GF_EXP[i]
        for j, c in enumerate(poly):
            nxt[j] ^= c
            nxt[j + 1] ^= _gf_mul(c, factor)
        poly = nxt
    return poly


def _rs_encode(data: List[int], ec_len: int) -> List[int]:
    gen = _rs_generator(ec_len)
    rem = [0] * ec_len
    for byte in data:
        factor = byte ^ rem[0]
        rem = rem[1:] + [0]
        for j in range(ec_len):
            rem[j] ^= _gf_mul(gen[j + 1], factor)
    return rem


def _format_bits(mask: int) -> int:
    # ECC Level L = 01
    data = (0b01 << 3) | mask
    rem = data << 10
    for i in range(14, 9, -1):
        if (rem >> i) & 1:
            rem ^= 0x537 << (i - 10)
    return ((data << 10) | rem) ^ 0x5412


def _version_bits(ver: int) -> int:
    rem = ver << 12
    for i in range(17, 11, -1):
        if (rem >> i) & 1:
            rem ^= 0x1F25 << (i - 12)
    return (ver << 12) | rem


def encode_qr_matrix(text: str) -> List[List[bool]]:
    payload = text.encode("utf-8")
    n = len(payload)

    ver = 0
    for v in range(1, 11):
        _, _, b1, d1, b2, d2, _ = _QR_L_SPEC[v]
        cap = b1 * d1 + b2 * d2
        overhead = 2 if v <= 9 else 3  # 4-bit mode + 8/16-bit count + 4-bit term
        if n + overhead <= cap:
            ver = v
            break
    if ver == 0:
        raise ValueError(f"Payload too long ({n} bytes) for QR v1-v10")

    _, ec_len, b1, d1, b2, d2, aligns = _QR_L_SPEC[ver]
    data_cap = b1 * d1 + b2 * d2

    bits: List[int] = [0, 1, 0, 0]  # Byte mode (0100)
    cc_bits = 8 if ver <= 9 else 16
    for i in range(cc_bits - 1, -1, -1):
        bits.append((n >> i) & 1)
    for byte in payload:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)

    term = min(4, data_cap * 8 - len(bits))
    bits.extend([0] * term)
    while len(bits) % 8 != 0:
        bits.append(0)

    codewords: List[int] = []
    for i in range(0, len(bits), 8):
        val = 0
        for b in bits[i : i + 8]:
            val = (val << 1) | b
        codewords.append(val)

    pad_bytes = [0xEC, 0x11]
    idx = 0
    while len(codewords) < data_cap:
        codewords.append(pad_bytes[idx % 2])
        idx += 1

    blocks_data: List[List[int]] = []
    blocks_ec: List[List[int]] = []
    pos = 0
    for _ in range(b1):
        blk = codewords[pos : pos + d1]
        pos += d1
        blocks_data.append(blk)
        blocks_ec.append(_rs_encode(blk, ec_len))
    for _ in range(b2):
        blk = codewords[pos : pos + d2]
        pos += d2
        blocks_data.append(blk)
        blocks_ec.append(_rs_encode(blk, ec_len))

    final_bytes: List[int] = []
    max_d = max(d1, d2)
    for i in range(max_d):
        for blk in blocks_data:
            if i < len(blk):
                final_bytes.append(blk[i])
    for i in range(ec_len):
        for ec in blocks_ec:
            final_bytes.append(ec[i])

    size = ver * 4 + 17
    matrix = [[False] * size for _ in range(size)]
    is_func = [[False] * size for _ in range(size)]

    def set_func(r: int, c: int, dark: bool):
        if 0 <= r < size and 0 <= c < size:
            matrix[r][c] = dark
            is_func[r][c] = True

    def place_finder(tr: int, tc: int):
        for dr in range(-1, 8):
            for dc in range(-1, 8):
                r, c = tr + dr, tc + dc
                if 0 <= r < size and 0 <= c < size:
                    in_outer = 0 <= dr <= 6 and 0 <= dc <= 6 and (dr in (0, 6) or dc in (0, 6))
                    in_inner = 2 <= dr <= 4 and 2 <= dc <= 4
                    set_func(r, c, in_outer or in_inner)

    place_finder(0, 0)
    place_finder(0, size - 7)
    place_finder(size - 7, 0)

    for i in range(8, size - 8):
        set_func(6, i, i % 2 == 0)
        set_func(i, 6, i % 2 == 0)

    for ar in aligns:
        for ac in aligns:
            if (ar == 6 and ac == 6) or (ar == 6 and ac == aligns[-1]) or (ar == aligns[-1] and ac == 6):
                continue
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    dark = max(abs(dr), abs(dc)) in (0, 2)
                    set_func(ar + dr, ac + dc, dark)

    # Reserve format info & dark module
    for i in range(9):
        if i != 6:
            is_func[8][i] = True
            is_func[i][8] = True
    for i in range(8):
        is_func[8][size - 1 - i] = True
        is_func[size - 1 - i][8] = True
    set_func(size - 8, 8, True)

    if ver >= 7:
        vbits = _version_bits(ver)
        for i in range(18):
            bit = ((vbits >> i) & 1) == 1
            r, c = i // 3, size - 11 + (i % 3)
            set_func(r, c, bit)
            set_func(c, r, bit)

    stream_bits: List[bool] = []
    for byte in final_bytes:
        for i in range(7, -1, -1):
            stream_bits.append(((byte >> i) & 1) == 1)

    bit_idx = 0
    upward = True
    col = size - 1
    while col > 0:
        if col == 6:
            col -= 1
        rows = range(size - 1, -1, -1) if upward else range(size)
        for r in rows:
            for dc in (0, -1):
                c = col + dc
                if not is_func[r][c]:
                    dark = stream_bits[bit_idx] if bit_idx < len(stream_bits) else False
                    bit_idx += 1
                    # Mask 0: (r + c) % 2 == 0
                    if (r + c) % 2 == 0:
                        dark = not dark
                    matrix[r][c] = dark
        upward = not upward
        col -= 2

    fbits = _format_bits(0)
    coords_a: List[Tuple[int, int]] = [
        (8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7), (8, 8),
        (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8),
    ]
    for i, (r, c) in enumerate(coords_a):
        matrix[r][c] = ((fbits >> (14 - i)) & 1) == 1
    for i in range(7):
        matrix[size - 1 - i][8] = ((fbits >> (14 - i)) & 1) == 1
    for i in range(8):
        matrix[8][size - 8 + i] = ((fbits >> (7 - i)) & 1) == 1

    return matrix


def render_qr_svg(text: str, module_px: int = 7, border: int = 3, fg: str = "#070A12", bg: str = "#FFFFFF") -> str:
    matrix = encode_qr_matrix(text)
    size = len(matrix)
    total = (size + border * 2) * module_px
    rects = []
    for r, row in enumerate(matrix):
        y = (r + border) * module_px
        for c, dark in enumerate(row):
            if dark:
                x = (c + border) * module_px
                rects.append(f'<rect x="{x}" y="{y}" width="{module_px}" height="{module_px}"/>')
    body = "".join(rects)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total} {total}" '
        f'width="{total}" height="{total}" shape-rendering="crispEdges">'
        f'<rect width="{total}" height="{total}" rx="12" fill="{bg}"/>'
        f'<g fill="{fg}">{body}</g></svg>'
    )

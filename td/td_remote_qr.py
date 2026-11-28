# Text DAT `qr` inside the TD Remote component: a QR code encoder in plain Python (byte mode, error
# correction M, versions 1-10, up to 213 bytes), so the component draws its own pairing QR with no
# internet and nothing to install. matrix(text) returns rows of booleans, True = dark.

# version: (EC codewords per block, [(blocks, data codewords per block), ...])
ECC = {1: (10, [(1, 16)]), 2: (16, [(1, 28)]), 3: (26, [(1, 44)]), 4: (18, [(2, 32)]), 5: (24, [(2, 43)]),
	6: (16, [(4, 27)]), 7: (18, [(4, 31)]), 8: (22, [(2, 38), (2, 39)]), 9: (22, [(3, 36), (2, 37)]),
	10: (26, [(4, 43), (1, 44)])}
ALIGN = {1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30], 6: [6, 34], 7: [6, 22, 38], 8: [6, 24, 42],
	9: [6, 26, 46], 10: [6, 28, 50]}
MASKS = [lambda x, y: (x + y) % 2 == 0, lambda x, y: y % 2 == 0, lambda x, y: x % 3 == 0,
	lambda x, y: (x + y) % 3 == 0, lambda x, y: (x // 3 + y // 2) % 2 == 0,
	lambda x, y: x * y % 2 + x * y % 3 == 0, lambda x, y: (x * y % 2 + x * y % 3) % 2 == 0,
	lambda x, y: ((x + y) % 2 + x * y % 3) % 2 == 0]

EXP, LOG = [0] * 512, [0] * 256
_x = 1
for _i in range(255):
	EXP[_i], LOG[_x] = _x, _i
	_x <<= 1
	if _x & 0x100:
		_x ^= 0x11D
for _i in range(255, 512):
	EXP[_i] = EXP[_i - 255]

def _mul(a, b):
	return 0 if a == 0 or b == 0 else EXP[LOG[a] + LOG[b]]

def _ecc(data, n):
	# Reed-Solomon: the remainder of data * x^n divided by the generator polynomial
	g = [1]
	for i in range(n):
		g = [(g[j] if j < len(g) else 0) ^ (_mul(g[j - 1], EXP[i]) if j else 0) for j in range(len(g) + 1)]
	res = [0] * n
	for d in data:
		f = d ^ res[0]
		res = res[1:] + [0]
		for j in range(n):
			res[j] ^= _mul(g[j + 1], f)
	return res

def _codewords(data):
	for ver in range(1, 11):
		ec, groups = ECC[ver]
		cap, cc = sum(c * d for c, d in groups), 8 if ver < 10 else 16
		if 4 + cc + 8 * len(data) <= cap * 8:
			break
	else:
		raise ValueError('too long for a QR code here: %d bytes' % len(data))
	bits = []
	def put(v, n):
		bits.extend((v >> i) & 1 for i in range(n - 1, -1, -1))
	put(0b0100, 4)
	put(len(data), cc)
	for b in data:
		put(b, 8)
	put(0, min(4, cap * 8 - len(bits)))
	put(0, -len(bits) % 8)
	out = [int(''.join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]
	pad = 0xEC
	while len(out) < cap:
		out.append(pad)
		pad ^= 0xEC ^ 0x11
	blocks, i = [], 0
	for count, n in groups:
		for _ in range(count):
			blocks.append(out[i:i + n])
			i += n
	eccs = [_ecc(b, ec) for b in blocks]
	inter = [b[k] for k in range(max(map(len, blocks))) for b in blocks if k < len(b)]
	inter += [e[k] for k in range(ec) for e in eccs]
	return ver, inter

def _penalty(m):
	n, score = len(m), 0
	lines = m + [list(c) for c in zip(*m)]
	for row in lines:
		run = 1
		for a, b in zip(row, row[1:]):
			if a == b:
				run += 1
			else:
				score += run - 2 if run >= 5 else 0
				run = 1
		score += run - 2 if run >= 5 else 0
		s = ''.join('1' if v else '0' for v in row)
		score += 40 * (s.count('10111010000') + s.count('00001011101'))
	for y in range(n - 1):
		for x in range(n - 1):
			if m[y][x] == m[y][x + 1] == m[y + 1][x] == m[y + 1][x + 1]:
				score += 3
	dark = sum(map(sum, m))
	return score + abs(dark * 20 - n * n * 10) // (n * n) * 10

def matrix(text, mask=None):
	ver, data = _codewords(text.encode('utf-8'))
	size = 17 + 4 * ver
	mod = [[False] * size for _ in range(size)]
	fn = [[False] * size for _ in range(size)]
	def put(x, y, dark):
		mod[y][x], fn[y][x] = dark, True
	for i in range(size):
		put(6, i, i % 2 == 0)
		put(i, 6, i % 2 == 0)
	for cx, cy in ((3, 3), (size - 4, 3), (3, size - 4)):
		for dy in range(-4, 5):
			for dx in range(-4, 5):
				if 0 <= cx + dx < size and 0 <= cy + dy < size:
					put(cx + dx, cy + dy, max(abs(dx), abs(dy)) not in (2, 4))
	pos = ALIGN[ver]
	for i, ay in enumerate(pos):
		for j, ax in enumerate(pos):
			if (i, j) in ((0, 0), (0, len(pos) - 1), (len(pos) - 1, 0)):
				continue
			for dy in range(-2, 3):
				for dx in range(-2, 3):
					put(ax + dx, ay + dy, max(abs(dx), abs(dy)) != 1)
	def format_bits(mk):
		d = mk  # error correction M is 00
		r = d
		for _ in range(10):
			r = (r << 1) ^ ((r >> 9) * 0x537)
		b = ((d << 10) | r) ^ 0x5412
		bit = lambda i: (b >> i) & 1 == 1
		for i in range(6):
			put(8, i, bit(i))
		put(8, 7, bit(6))
		put(8, 8, bit(7))
		put(7, 8, bit(8))
		for i in range(9, 15):
			put(14 - i, 8, bit(i))
		for i in range(8):
			put(size - 1 - i, 8, bit(i))
		for i in range(8, 15):
			put(8, size - 15 + i, bit(i))
		put(8, size - 8, True)
	format_bits(0)  # reserves the format area before the data goes in
	if ver >= 7:
		r = ver
		for _ in range(12):
			r = (r << 1) ^ ((r >> 11) * 0x1F25)
		b = (ver << 12) | r
		for i in range(18):
			a, c, dark = size - 11 + i % 3, i // 3, (b >> i) & 1 == 1
			put(a, c, dark)
			put(c, a, dark)
	i, right = 0, size - 1
	while right >= 1:
		if right == 6:
			right = 5
		for vert in range(size):
			for j in range(2):
				x = right - j
				y = size - 1 - vert if ((right + 1) & 2) == 0 else vert
				if not fn[y][x] and i < len(data) * 8:
					mod[y][x] = (data[i >> 3] >> (7 - (i & 7))) & 1 == 1
					i += 1
		right -= 2
	def masked(mk):
		f = MASKS[mk]
		return [[mod[y][x] ^ (not fn[y][x] and f(x, y)) for x in range(size)] for y in range(size)]
	if mask is None:
		mask = min(range(8), key=lambda mk: (format_bits(mk), _penalty(masked(mk)))[1])
	format_bits(mask)
	return masked(mask)

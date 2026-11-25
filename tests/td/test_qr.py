# orrery_qr.py (the QR encoder) and orrery_qrtop.py (the Script TOP that draws it). Every code is
# decoded back with zxing-cpp, an independent reader, so "it scans" is what is tested.
import numpy
import pytest
import zxingcpp

from tdfake import load_module, COMP

QR = load_module('orrery_qr.py', COMP('orrery'))


def image(m, cell=4, quiet=4):
	"""The matrix as a grayscale picture: black modules on white, with a quiet zone."""
	n = len(m) + 2 * quiet
	a = numpy.full((n, n), 255, numpy.uint8)
	for y, row in enumerate(m):
		for x, dark in enumerate(row):
			if dark:
				a[y + quiet, x + quiet] = 0
	return numpy.kron(a, numpy.ones((cell, cell), numpy.uint8))


def decode(img):
	found = zxingcpp.read_barcodes(img)
	assert found, 'no QR code found'
	assert found[0].format == zxingcpp.BarcodeFormat.QRCode
	return found[0].text


def version_of(m):
	return (len(m) - 17) // 4


# --- what the component actually encodes ---------------------------------------------------

@pytest.mark.parametrize('text', [
	'http://192.168.1.20:9980/?code=042137',
	'http://10.0.0.5:65535/?code=000000',
	'http://127.0.0.1:1024/?code=999999',
	'http://[fe80::1]:9980/?code=123456',
])
def test_pairing_addresses_scan_back(text):
	assert decode(image(QR.matrix(text))) == text


def test_a_pairing_address_fits_a_small_code():
	# about 40 bytes: version 3 (29 x 29), easy to scan off a laptop screen
	m = QR.matrix('http://192.168.100.200:65535/?code=123456')
	assert version_of(m) <= 3


# --- the encoder across its range ----------------------------------------------------------

# the largest byte count each version holds at error correction M
CAPACITY = {1: 14, 2: 26, 3: 42, 4: 62, 5: 84, 6: 106, 7: 122, 8: 152, 9: 180, 10: 213}


@pytest.mark.parametrize('version,length', sorted(CAPACITY.items()))
def test_each_version_at_full_capacity_scans(version, length):
	text = ''.join(chr(ord('a') + i % 26) for i in range(length))
	m = QR.matrix(text)
	assert version_of(m) == version
	assert decode(image(m)) == text


@pytest.mark.parametrize('version,length', sorted(CAPACITY.items())[:-1])  # past version 10: the too-long test
def test_one_byte_more_needs_the_next_version(version, length):
	assert version_of(QR.matrix('x' * (length + 1))) == version + 1


def test_too_long_is_an_error():
	with pytest.raises(ValueError, match='too long'):
		QR.matrix('x' * 214)


@pytest.mark.parametrize('mask', range(8))
def test_every_mask_scans(mask):
	text = 'http://192.168.1.20:9980/?code=042137'
	assert decode(image(QR.matrix(text, mask=mask))) == text


def test_utf8_text_scans():
	text = 'http://orrery.local:9980/?code=123456&n=Señal ✦'
	assert decode(image(QR.matrix(text))) == text


def test_size_is_17_plus_4_per_version():
	for text in ('a', 'x' * 100, 'x' * 213):
		m = QR.matrix(text)
		assert len(m) == 17 + 4 * version_of(m)
		assert all(len(row) == len(m) for row in m)


def test_finder_patterns_in_three_corners():
	m = QR.matrix('http://192.168.1.20:9980/?code=042137')
	n = len(m)
	for cx, cy in ((0, 0), (n - 7, 0), (0, n - 7)):
		ring = [m[cy][cx + i] for i in range(7)] + [m[cy + 6][cx + i] for i in range(7)]
		assert all(ring), (cx, cy)
		assert m[cy + 3][cx + 3]           # the centre is dark
		assert not m[cy + 1][cx + 1]       # with a light ring around it


def test_same_text_same_code():
	a = QR.matrix('http://192.168.1.20:9980/?code=042137')
	assert a == QR.matrix('http://192.168.1.20:9980/?code=042137')
	assert a != QR.matrix('http://192.168.1.20:9980/?code=042138')


def test_reed_solomon_matches_a_known_vector():
	# "HELLO WORLD" 1-M, from the QR specification's worked example (thonky.com tutorial)
	data = [32, 91, 11, 120, 209, 114, 220, 77, 67, 64, 236, 17, 236, 17, 236, 17]
	assert QR._ecc(data, 10) == [196, 35, 39, 119, 235, 215, 231, 226, 93, 23]


# --- the Script TOP --------------------------------------------------------------------------

def top_image(world):
	img = world.draw_qr()
	assert img.dtype == numpy.uint8 and img.ndim == 3 and img.shape[2] == 4
	return img


def test_qrtop_draws_the_pairing_address(world):
	world.orrery.par.Address = 'http://192.168.1.20:9980'
	img = top_image(world)
	gray = img[::-1, :, 0]  # TouchDesigner rows start at the bottom: flip back to read it
	assert decode(numpy.ascontiguousarray(gray)) == 'http://192.168.1.20:9980/?code=123456'


def test_qrtop_follows_a_new_code(world):
	world.orrery.par.Address = 'http://192.168.1.20:9980'
	world.orrery.par.Code = '654321'
	gray = numpy.ascontiguousarray(top_image(world)[::-1, :, 0])
	assert decode(gray) == 'http://192.168.1.20:9980/?code=654321'


def test_qrtop_is_opaque_with_a_white_quiet_zone(world):
	world.orrery.par.Address = 'http://192.168.1.20:9980'
	img = top_image(world)
	assert (img[:, :, 3] == 255).all()
	cell = 12
	border = 4 * cell
	assert (img[:border, :, :3] == 255).all() and (img[-border:, :, :3] == 255).all()
	assert (img[:, :border, :3] == 255).all() and (img[:, -border:, :3] == 255).all()


def test_qrtop_size_is_modules_plus_quiet_zone_times_12(world):
	world.orrery.par.Address = 'http://192.168.1.20:9980'
	img = top_image(world)
	n = len(world.qr.matrix('http://192.168.1.20:9980/?code=123456')) + 8
	assert img.shape[:2] == (n * 12, n * 12)


@pytest.mark.parametrize('address,code', [('', '123456'), ('http://192.168.1.20:9980', '')])
def test_qrtop_is_blank_until_there_is_an_address_and_a_code(world, address, code):
	world.orrery.par.Address = address
	world.orrery.par.Code = code
	img = top_image(world)
	assert (img[:, :, :3] == 255).all()

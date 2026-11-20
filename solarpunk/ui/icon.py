"""Solarpunk's icon (9.7, SP-030): a solarpunk, drawn by Ghost's brief: a Latina field engineer, blue collar and a
little gritty, in a work tank top, a short asymmetric cut (the cool-mom cut: cropped short on one side, height at the
crown, the long side swept forward and angled to her jaw), her hair and the glow around her made of plasma, a half-glass
visor over one eye for augmented sight, a grease smudge on her cheek, a wrench over her shoulder, on a night disc ringed
in sun-gold like a work badge. She is drawn here from shapes and a plasma field, sample by sample, so no image file
enters the repository (C-033); pixels() gives RGBA rows, png() and ico() the bytes a window and a desktop shortcut wear.
No tkinter, so the fast loop tests it. Each pixel is the mean of several samples, so her edges are smooth at every
size. A rendered artwork may replace the drawing later, under its own decision."""
import math
import struct
import zlib

Colour = tuple[int, int, int, int]
CLEAR: Colour = (0, 0, 0, 0)
NIGHT = (14, 22, 44)
RING = (226, 178, 74)
SKIN = (172, 110, 72)
BROW = (48, 26, 20)
EYE = (30, 16, 18)
LIPS = (146, 44, 70)
GOLD = (236, 190, 86)
TANK = (84, 98, 110)
GRIME = (58, 66, 74)
GREASE = (96, 62, 44)
STEEL = (196, 206, 214)
STEEL_EDGE = (70, 80, 92)
# The plasma's colours from cool to white-hot: violet, magenta, sun-orange, gold, near white.
PLASMA = ((96, 24, 150), (232, 44, 170), (255, 128, 30), (255, 220, 70), (255, 250, 220))
GLOW = 1.4
SIZES = (16, 24, 32, 48, 64, 128, 256)


def plasma(x: float, y: float) -> tuple[int, int, int]:
    """The plasma's colour at a point of the 64-unit canvas: four sine waves summed, read along PLASMA; the same point
    gives the same colour, so the plasma does not flicker between sizes."""
    v = math.sin(x / 3.0) + math.sin(y / 4.0) + math.sin((x + y) / 5.0) + math.sin(math.hypot(x - 32, y - 32) / 2.5)
    t = min(max((v + 4) / 8, 0.0), 1.0) * (len(PLASMA) - 1)
    low = int(t)
    high = min(low + 1, len(PLASMA) - 1)
    share = t - low
    return tuple(round(a + (b - a) * share) for a, b in zip(PLASMA[low], PLASMA[high]))  # type: ignore[return-value]


def near_segment(x: float, y: float, a: tuple[float, float], b: tuple[float, float], radius: float) -> bool:
    """Whether a point lies within radius of the segment from a to b: the wrench's shaft and its jaw's cut."""
    ax, ay = a
    bx, by = b
    span = (bx - ax) ** 2 + (by - ay) ** 2
    share = 0.0 if span == 0 else min(max(((x - ax) * (bx - ax) + (y - ay) * (by - ay)) / span, 0.0), 1.0)
    return math.hypot(x - (ax + share * (bx - ax)), y - (ay + share * (by - ay))) <= radius


def in_ellipse(x: float, y: float, centre: tuple[float, float], rx: float, ry: float) -> bool:
    """Whether a point is inside an upright ellipse."""
    return ((x - centre[0]) / rx) ** 2 + ((y - centre[1]) / ry) ** 2 <= 1


def in_face(x: float, y: float) -> bool:
    """Her face and the ear on her shaved side."""
    return in_ellipse(x, y, (30, 27), 8.2, 10.4) or in_ellipse(x, y, (21.6, 27.5), 1.6, 2.4)


def in_skull(x: float, y: float) -> bool:
    """The crown of her head, above the brow, and its short side down to her ear: the cropped half's ground."""
    return in_ellipse(x, y, (30, 25), 9.9, 12.3) and (y < 21 or (x < 23.6 and y < 25.5))


def in_hair(x: float, y: float) -> bool:
    """Her hair's long side: swept from a side part over the crown, a lock across her temple, cut at an angle at her
    jaw on the right."""
    crown = in_ellipse(x, y, (31.5, 23), 11, 13.6) and y < 22 and x >= 25 + (21 - y) * 0.3
    temple = in_ellipse(x, y, (37.2, 23), 3.0, 6.5)
    fall = 20 <= y <= 35.5 - (x - 37) * 0.5 and 36.5 <= x <= 41.2 + (y - 20) * 0.08
    return crown or temple or fall


def in_shoulders(x: float, y: float) -> bool:
    """Her bare shoulders and arms, below her neck."""
    return y >= 40 and abs(x - 30) <= 8 + (y - 40) * 1.15


def in_tank(x: float, y: float) -> bool:
    """Her work tank top: its front from a scooped neckline down, and its two straps over her shoulders."""
    scoop = 44.5 + 1.2 * math.cos((x - 30) / 4.0)
    front = y >= scoop and abs(x - 30) <= 7 + (y - 44) * 0.45
    straps = near_segment(x, y, (25.2, 40.2), (24.4, 46), 1.15) or near_segment(x, y, (34.8, 40.2), (35.6, 46), 1.15)
    return front or straps


def in_neckline(x: float, y: float) -> bool:
    """Her neck down to the tank's neckline, skin."""
    return 26.5 <= x <= 33.5 and 33 <= y <= 41


def in_figure(x: float, y: float) -> bool:
    """Her whole silhouette, for the plasma glow around it."""
    return in_face(x, y) or in_skull(x, y) or in_hair(x, y) or in_neckline(x, y) or in_shoulders(x, y)


def in_wrench(x: float, y: float) -> bool:
    """The wrench behind her, over her shaved shoulder: its shaft from behind her back up to the left, its head a
    ring with the jaw open toward the upper left."""
    shaft = near_segment(x, y, (40, 50), (15, 16), 2.1)
    ring = math.hypot(x - 13.2, y - 13.2) <= 5.6
    jaw = near_segment(x, y, (13.2, 13.2), (6, 6), 2.4)
    return (shaft or ring) and not jaw


def in_wrench_core(x: float, y: float) -> bool:
    """Whether a wrench point is inside its edge, by a unit: the steel, the edge darker around it."""
    return all(in_wrench(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))


def feature_at(x: float, y: float) -> Colour | None:
    """Her face's features, front of all: brows, almond eyes with a light, lips, a gold hoop at her ear, a smudge of
    grease on her cheek; None elsewhere."""
    for cx in (26.4, 33.6):
        if in_ellipse(x, y, (cx, 25.2), 2.3, 0.95):
            return (240, 230, 220, 255) if abs(x - cx - 0.6) < 0.45 and abs(y - 24.9) < 0.4 else (*EYE, 255)
        if in_ellipse(x, y, (cx, 22.4), 2.6, 0.6) and y < 22.6:
            return (*BROW, 255)
    if in_ellipse(x, y, (30, 31.7), 2.1, 0.85):
        return (*LIPS, 255)
    if 1.6 <= math.hypot(x - 21.4, y - 31.6) <= 2.3:
        return (*GOLD, 255)
    if in_ellipse(x, y, (25.2, 29.8), 2.1, 0.7) and (int(x * 4) + int(y * 3)) % 3:
        return (*GREASE, 255)
    return None


def cropped(x: float, y: float) -> Colour:
    """Her hair's short side: the plasma, darker and textured, cropped close."""
    dark = 0.62 if (int(x * 2.5) + int(y * 1.5)) % 3 else 0.8
    return (*(round(c * dark) for c in plasma(x, y)), 255)  # type: ignore[return-value]


def skin(x: float) -> Colour:
    """Her skin, the sun on her left: a little darker toward her right cheek."""
    shade = 1 - 0.16 * min(max((x - 27) / 10, 0.0), 1.0)
    return (*(round(c * shade) for c in SKIN), 255)  # type: ignore[return-value]


VISOR_GLASS = (80, 232, 220)
VISOR_FRAME = (36, 46, 58)
GLASS_SHARE = 0.42


def in_lens(x: float, y: float) -> bool:
    """The visor's half glass over her left eye, a slanted pane from her temple to the bridge of her nose."""
    return 22.4 <= x <= 30.4 and 22.3 + (x - 22.4) * 0.06 <= y <= 27.9 - (x - 22.4) * 0.14


def visor_at(x: float, y: float) -> Colour | None:
    """The visor where it covers the sample, as a colour to lay over what is under it: the earpiece and the glass's
    frame dark and opaque, the reticle bright, the glass a cyan tint (its alpha the tint's share); None elsewhere."""
    if near_segment(x, y, (21.2, 26.8), (22.8, 24.4), 0.55):
        return (*VISOR_FRAME, 255)
    if not in_lens(x, y):
        return None
    if not all(in_lens(x + dx, y + dy) for dx, dy in ((0.45, 0), (-0.45, 0), (0, 0.45), (0, -0.45))):
        return (*VISOR_FRAME, 255)
    reach = math.hypot(x - 26.4, y - 25.2)
    if 1.55 <= reach <= 1.95 and not (abs(x - 26.4) < 0.5 or abs(y - 25.2) < 0.5):
        return (210, 255, 250, 255)
    return (*VISOR_GLASS, round(255 * GLASS_SHARE))


def colour_at(x: float, y: float) -> Colour:
    """The colour of one sample, the visor laid over her: an opaque part of it replaces what is under it, its glass
    tints it."""
    under = base_colour(x, y)
    over = visor_at(x, y)
    if over is None or under[3] == 0:
        return under
    share = over[3] / 255
    mixed = tuple(round(u * (1 - share) + o * share) for u, o in zip(under[:3], over[:3]))
    return (*mixed, 255)  # type: ignore[return-value]


def base_colour(x: float, y: float) -> Colour:
    """The colour of one sample of the 64-unit canvas, front to back: the gold ring and clear outside it, so she sits
    in the badge; her features, her plasma hair, her face, the shaved side with its glint, her neck, her tank (worn,
    with grime), her bare shoulders, the wrench, the plasma glow around her, the night disc."""
    centre = math.hypot(x - 32, y - 32)
    if centre > 31.5:
        return CLEAR
    if centre >= 30.2:
        return (*RING, 255)
    found = feature_at(x, y)
    if found is not None:
        return found
    if in_hair(x, y):
        return (*plasma(x, y), 255)
    if in_skull(x, y) and (not in_face(x, y) or y < 17 or x < 23.6):
        return cropped(x, y)
    if in_face(x, y) or in_neckline(x, y) and not in_tank(x, y):
        return skin(x)
    if in_tank(x, y):
        return (*GRIME, 255) if (int(x * 2.3) * 7 + int(y * 1.7) * 13) % 11 == 0 else (*TANK, 255)
    if in_shoulders(x, y):
        return skin(x)
    if in_wrench(x, y):
        return (*STEEL, 255) if in_wrench_core(x, y) else (*STEEL_EDGE, 255)
    if any(in_figure(x + dx * GLOW, y + dy * GLOW) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
        return (*plasma(x, y), 255)
    return (*NIGHT, 255)


def samples_for(size: int) -> int:
    """How many samples a side each pixel takes: 4 up to 64 px, 2 above, so the 256 px icon is made in seconds."""
    return 4 if size <= 64 else 2


def pixels(size: int) -> list[list[Colour]]:
    """The icon as size rows of size RGBA pixels, each the mean of its samples: pixels(64)[0][0] is clear (outside the
    disc), pixels(64)[32][32] opaque."""
    scale = 64 / size
    per = samples_for(size)
    rows = []
    for row in range(size):
        line = []
        for column in range(size):
            found = [colour_at((column + (i + 0.5) / per) * scale, (row + (j + 0.5) / per) * scale)
                     for i in range(per) for j in range(per)]
            alpha = sum(c[3] for c in found)
            if alpha == 0:
                line.append(CLEAR)
                continue
            mixed = tuple(round(sum(c[k] * c[3] for c in found) / alpha) for k in range(3))
            line.append((*mixed, round(alpha / len(found))))  # type: ignore[arg-type]
        rows.append(line)
    return rows


def chunk(kind: bytes, data: bytes) -> bytes:
    """One PNG chunk: its length, its kind, its data and the CRC of kind and data."""
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def png(size: int) -> bytes:
    """The icon as PNG bytes, RGBA, size by size: png(64) starts with the PNG signature."""
    raw = b"".join(b"\x00" + bytes(value for pixel in line for value in pixel) for line in pixels(size))
    header = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def ico(sizes: tuple[int, ...] = SIZES) -> bytes:
    """A Windows .ico holding the icon at each size as PNG (as Windows Vista and later read): its header counts the
    sizes, each entry giving a size (0 for 256), 32 bits per pixel, and where its PNG starts."""
    images = [png(size) for size in sizes]
    offset = 6 + 16 * len(images)
    entries = b""
    for size, image in zip(sizes, images):
        side = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", side, side, 0, 0, 1, 32, len(image), offset)
        offset += len(image)
    return struct.pack("<HHH", 0, 1, len(images)) + entries + b"".join(images)

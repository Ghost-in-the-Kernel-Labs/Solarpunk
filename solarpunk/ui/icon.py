"""Solarpunk's icon (9.7, SP-030, SP-031): a solarpunk, by Ghost's brief: a Latina field engineer, blue collar and a
little gritty, in a work tank, plasma hair in a short asymmetric cut, an AR visor, a grease smudge, a wrench over her
shoulder, on a night disc ringed in sun-gold like a work badge. Ghost had her painted (SP-031: his, released CC0) and
she is kept in solarpunk/ui/art/ as one RGBA PNG a size, each tuned for its size: 256 and 128 downscaled from the
painting; 64 and 48 downscaled and sharpened, their ring taken from a clean downscale; 32 and 24 drawn from
solarpunk_small.svg and 16 from solarpunk_tiny.svg, because the painting turns to mud below 48. png() gives a size's
bytes and ico() the Windows icon holding them all. No tkinter, so the fast loop tests it."""
import struct
from pathlib import Path

ART = Path(__file__).resolve().parent / "art"
SIZES = (16, 24, 32, 48, 64, 128, 256)


def art_file(size: int) -> Path:
    """The PNG for a size: art_file(32) is solarpunk/ui/art/solarpunk_32.png; a size with no file raises ValueError."""
    if size not in SIZES:
        raise ValueError(f"no icon at {size} px; the sizes are {', '.join(map(str, SIZES))}")
    return ART / f"solarpunk_{size}.png"


def png(size: int) -> bytes:
    """The icon as PNG bytes at a size: png(64) starts with the PNG signature and is 64 by 64, RGBA."""
    return art_file(size).read_bytes()


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

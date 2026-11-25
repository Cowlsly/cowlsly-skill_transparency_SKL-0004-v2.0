"""Deterministic synthetic fixture corpus for Transparency Assurance v2.

Each case builds a small, license-clean PNG (or one JPEG) in a caller-supplied
directory and declares the gate statuses we expect from inspect_asset.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


Builder = Callable[[Path], Path]


@dataclass(frozen=True)
class FixtureCase:
    id: str
    profile: str
    builder: Builder
    expected_compliant: bool
    expected_gates: dict[str, str]
    expected_edge_mode: str | None = None
    notes: str = ""
    filename: str = ""

    def output_name(self) -> str:
        return self.filename or f"{self.id}.png"


def _save(path: Path, im: Image.Image, **save_kw) -> Path:
    im.save(path, **save_kw)
    return path


def _circle(size: int = 160, fill=(30, 120, 220, 255), radius: int | None = None) -> Image.Image:
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    c = size // 2
    r = radius if radius is not None else max(8, size // 4)
    ImageDraw.Draw(im).ellipse((c - r, c - r, c + r, c + r), fill=fill)
    return im


def _fringe_around(subject: Image.Image, colour: tuple[int, int, int, int], max_filter: int = 5) -> Image.Image:
    core = subject.split()[-1].point(lambda a: 255 if a >= 250 else 0)
    ring = core.filter(ImageFilter.MaxFilter(max_filter))
    fringe = Image.new("RGBA", subject.size, (0, 0, 0, 0))
    for y in range(subject.height):
        for x in range(subject.width):
            if ring.getpixel((x, y)) == 255 and core.getpixel((x, y)) == 0:
                fringe.putpixel((x, y), colour)
    return Image.alpha_composite(fringe, subject)


def _checker(size: int = 128, tile: int = 16) -> Image.Image:
    im = Image.new("RGBA", (size, size), (0, 0, 0, 255))
    d = ImageDraw.Draw(im)
    for y in range(0, size, tile):
        for x in range(0, size, tile):
            c = (224, 224, 224, 255) if ((x // tile + y // tile) % 2 == 0) else (184, 184, 184, 255)
            d.rectangle((x, y, x + tile - 1, y + tile - 1), fill=c)
    return im


def build_clean_ellipse(dest: Path) -> Path:
    return _save(dest, _circle())


def build_hard_rect(dest: Path) -> Path:
    im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle((40, 40, 120, 120), fill=(20, 90, 200, 255))
    return _save(dest, im)


def build_opaque_rgb(dest: Path) -> Path:
    return _save(dest, Image.new("RGB", (128, 128), (40, 80, 150)))


def build_opaque_rgba(dest: Path) -> Path:
    return _save(dest, Image.new("RGBA", (128, 128), (40, 80, 150, 255)))


def build_noise(dest: Path) -> Path:
    rng = np.random.default_rng(7)
    arr = np.zeros((128, 128, 4), dtype=np.uint8)
    arr[:, :, :3] = rng.integers(0, 255, size=(128, 128, 3), dtype=np.uint8)
    arr[:, :, 3] = rng.integers(1, 6, size=(128, 128), dtype=np.uint8)
    return _save(dest, Image.fromarray(arr, "RGBA"))


def build_nearly_empty(dest: Path) -> Path:
    im = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    im.putpixel((64, 64), (255, 0, 0, 255))
    return _save(dest, im)


def build_baked_checker(dest: Path) -> Path:
    return _save(dest, _checker())


def build_hidden_checker(dest: Path) -> Path:
    im = _checker()
    alpha = Image.new("L", im.size, 0)
    ImageDraw.Draw(alpha).ellipse((32, 32, 96, 96), fill=255)
    subject = Image.new("RGBA", im.size, (40, 120, 220, 255))
    im.putalpha(alpha)
    subject.putalpha(alpha)
    im.alpha_composite(subject)
    return _save(dest, im)


def build_plain_opaque_art(dest: Path) -> Path:
    im = Image.new("RGB", (128, 128), (40, 80, 150))
    ImageDraw.Draw(im).ellipse((24, 24, 104, 104), fill=(220, 120, 40))
    return _save(dest, im)


def build_white_halo(dest: Path) -> Path:
    return _save(dest, _fringe_around(_circle(), (236, 236, 236, 160)))


def build_chroma_spill(dest: Path) -> Path:
    return _save(dest, _fringe_around(_circle(fill=(30, 80, 210, 255)), (40, 220, 50, 180)))


def build_contact_shadow(dest: Path) -> Path:
    size = 180
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse((50, 100, 130, 150), fill=(18, 18, 18, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=6))
    subject = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(subject).ellipse((50, 40, 130, 120), fill=(30, 120, 220, 255))
    return _save(dest, Image.alpha_composite(shadow, subject))


def build_glow(dest: Path) -> Path:
    size = 180
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
    for radius, alpha in ((70, 30), (62, 60), (54, 100), (48, 150)):
        d.ellipse((90 - radius, 90 - radius, 90 + radius, 90 + radius), fill=(40, 130, 230, alpha))
    subject = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(subject).ellipse((50, 50, 130, 130), fill=(30, 120, 220, 255))
    return _save(dest, Image.alpha_composite(glow, subject))


def build_hair(dest: Path) -> Path:
    size = 180
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((60, 70, 120, 140), fill=(40, 24, 16, 255))
    rng = np.random.default_rng(11)
    for _ in range(70):
        x0 = int(rng.integers(70, 110))
        y0 = 74
        x1 = x0 + int(rng.integers(-28, 29))
        y1 = y0 - int(rng.integers(18, 50))
        d.line((x0, y0, x1, y1), fill=(36, 20, 12, 255), width=1)
    return _save(dest, im)


def build_glass(dest: Path) -> Path:
    im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((30, 30, 130, 130), radius=18, fill=(186, 220, 240, 96))
    return _save(dest, im)


def build_feature_ok(dest: Path) -> Path:
    return _save(dest, Image.new("RGB", (1024, 500), (30, 40, 50)), format="PNG")


def build_feature_alpha(dest: Path) -> Path:
    im = Image.new("RGBA", (1024, 500), (20, 20, 20, 255))
    im.putpixel((0, 0), (20, 20, 20, 0))
    return _save(dest, im)


def build_feature_wrong_size(dest: Path) -> Path:
    return _save(dest, Image.new("RGB", (800, 400), (30, 40, 50)), format="PNG")


def build_play_icon_alpha(dest: Path) -> Path:
    return _save(dest, _circle(size=512, radius=160))


def build_play_icon_opaque(dest: Path) -> Path:
    return _save(dest, Image.new("RGB", (512, 512), (20, 80, 160)), format="PNG")


def build_play_icon_wrong_size(dest: Path) -> Path:
    im = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse((40, 40, 216, 216), fill=(30, 120, 220, 255))
    return _save(dest, im)


def build_pwa_opaque(dest: Path) -> Path:
    return _save(dest, Image.new("RGB", (512, 512), (16, 32, 48)), format="PNG")


def build_pwa_alpha(dest: Path) -> Path:
    return _save(dest, _circle(size=512, radius=160))


def build_android_fg_alpha(dest: Path) -> Path:
    return _save(dest, _circle(size=256, radius=80))


def build_android_bg_opaque(dest: Path) -> Path:
    return _save(dest, Image.new("RGB", (256, 256), (10, 20, 40)), format="PNG")


def build_android_bg_alpha(dest: Path) -> Path:
    return _save(dest, _circle(size=256, radius=80))


def build_apple_fg_alpha(dest: Path) -> Path:
    return _save(dest, _circle(size=256, radius=80))


def build_apple_bg_opaque(dest: Path) -> Path:
    return _save(dest, Image.new("RGB", (256, 256), (200, 180, 140)), format="PNG")


def build_palette_trns(dest: Path) -> Path:
    im = Image.new("P", (128, 128), 0)
    palette = [0, 0, 0, 30, 120, 220] + [0] * (768 - 6)
    im.putpalette(palette)
    d = ImageDraw.Draw(im)
    d.ellipse((24, 24, 104, 104), fill=1)
    return _save(dest, im, format="PNG", transparency=0)


def build_rgb_trns(dest: Path) -> Path:
    im = Image.new("RGB", (128, 128), (255, 0, 255))
    ImageDraw.Draw(im).ellipse((24, 24, 104, 104), fill=(30, 120, 220))
    return _save(dest, im, format="PNG", transparency=(255, 0, 255))


def build_la_cutout(dest: Path) -> Path:
    im = Image.new("LA", (128, 128), (0, 0))
    ImageDraw.Draw(im).ellipse((24, 24, 104, 104), fill=(80, 255))
    return _save(dest, im, format="PNG")


def build_jpeg_opaque(dest: Path) -> Path:
    dest = dest.with_suffix(".jpg")
    Image.new("RGB", (128, 128), (40, 80, 150)).save(dest, "JPEG", quality=90)
    return dest


def build_clean_256(dest: Path) -> Path:
    return _save(dest, _circle(size=256, radius=80))


def build_truncated(dest: Path) -> Path:
    dest.write_bytes(b"\x89PNG\r\n\x1a\n" + b"not-a-real-image")
    return dest


CASES: list[FixtureCase] = [
    FixtureCase("clean_ellipse_repo_generic", "repo-generic", build_clean_ellipse, True, {"EDGE_QUALITY": "PASS", "MEANINGFUL_ALPHA_USAGE": "PASS", "FAKE_CHECKERBOARD": "PASS", "FILE_IDENTITY": "PASS"}, "clean"),
    FixtureCase("hard_rect_repo_generic", "repo-generic", build_hard_rect, True, {"EDGE_QUALITY": "PASS", "MEANINGFUL_ALPHA_USAGE": "PASS", "FAKE_CHECKERBOARD": "PASS"}, "clean"),
    FixtureCase("clean_ellipse_256", "repo-generic", build_clean_256, True, {"EDGE_QUALITY": "PASS", "MEANINGFUL_ALPHA_USAGE": "PASS"}, "clean"),
    FixtureCase("la_grayscale_cutout", "repo-generic", build_la_cutout, True, {"EDGE_QUALITY": "PASS", "MEANINGFUL_ALPHA_USAGE": "PASS", "TRANSPARENCY_CAPABILITY": "PASS"}),
    FixtureCase("palette_trns_repo_generic", "repo-generic", build_palette_trns, True, {"MEANINGFUL_ALPHA_USAGE": "PASS", "TRANSPARENCY_CAPABILITY": "PASS", "FILE_IDENTITY": "PASS"}),
    FixtureCase("rgb_trns_color_key", "repo-generic", build_rgb_trns, True, {"MEANINGFUL_ALPHA_USAGE": "PASS", "TRANSPARENCY_CAPABILITY": "PASS", "FILE_IDENTITY": "PASS"}),
    FixtureCase("opaque_rgb_repo_generic", "repo-generic", build_opaque_rgb, False, {"MEANINGFUL_ALPHA_USAGE": "FAIL", "EDGE_QUALITY": "NOT_APPLICABLE"}),
    FixtureCase("opaque_rgba_repo_generic", "repo-generic", build_opaque_rgba, False, {"MEANINGFUL_ALPHA_USAGE": "FAIL", "EDGE_QUALITY": "NOT_APPLICABLE"}),
    FixtureCase("jpeg_opaque_repo_generic", "repo-generic", build_jpeg_opaque, False, {"FILE_IDENTITY": "PASS", "MEANINGFUL_ALPHA_USAGE": "FAIL"}, filename="jpeg_opaque_repo_generic.jpg"),
    FixtureCase("near_transparent_noise", "repo-generic", build_noise, False, {"ALPHA_TOPOLOGY": "FAIL"}),
    FixtureCase("nearly_empty_one_pixel", "repo-generic", build_nearly_empty, False, {"ALPHA_TOPOLOGY": "FAIL"}),
    FixtureCase("baked_checkerboard", "repo-generic", build_baked_checker, False, {"FAKE_CHECKERBOARD": "FAIL"}),
    FixtureCase("hidden_checker_under_subject", "repo-generic", build_hidden_checker, True, {"FAKE_CHECKERBOARD": "PASS", "MEANINGFUL_ALPHA_USAGE": "PASS"}),
    FixtureCase("plain_opaque_art_not_checker", "repo-generic", build_plain_opaque_art, False, {"FAKE_CHECKERBOARD": "PASS", "MEANINGFUL_ALPHA_USAGE": "FAIL"}),
    FixtureCase("white_matte_halo", "repo-generic", build_white_halo, False, {"EDGE_QUALITY": "FAIL"}, "halo"),
    FixtureCase("chroma_spill_green", "repo-generic", build_chroma_spill, False, {"EDGE_QUALITY": "FAIL"}, "chroma_spill"),
    FixtureCase("contact_shadow", "repo-generic", build_contact_shadow, True, {"EDGE_QUALITY": "PASS", "MEANINGFUL_ALPHA_USAGE": "PASS"}, "shadow"),
    FixtureCase("subject_tinted_glow", "repo-generic", build_glow, True, {"EDGE_QUALITY": "PASS"}, "glow"),
    FixtureCase("hair_strands", "repo-generic", build_hair, True, {"EDGE_QUALITY": "PASS"}, "hair_fur"),
    FixtureCase("glass_translucency", "repo-generic", build_glass, True, {"EDGE_QUALITY": "PASS"}, "translucency"),
    FixtureCase("feature_graphic_ok", "google-play-feature-graphic", build_feature_ok, True, {"MEANINGFUL_ALPHA_USAGE": "PASS", "TRANSPARENCY_CAPABILITY": "NOT_APPLICABLE", "EDGE_QUALITY": "NOT_APPLICABLE", "TARGET_CONTRACT": "PASS"}),
    FixtureCase("feature_graphic_has_alpha", "google-play-feature-graphic", build_feature_alpha, False, {"MEANINGFUL_ALPHA_USAGE": "FAIL", "TARGET_CONTRACT": "FAIL"}),
    FixtureCase("feature_graphic_wrong_size", "google-play-feature-graphic", build_feature_wrong_size, False, {"TARGET_CONTRACT": "FAIL"}),
    FixtureCase("play_icon_512_alpha", "google-play-app-icon", build_play_icon_alpha, True, {"TARGET_CONTRACT": "PASS", "FILE_IDENTITY": "PASS"}),
    FixtureCase("play_icon_512_opaque", "google-play-app-icon", build_play_icon_opaque, False, {"TARGET_CONTRACT": "PASS", "EDGE_QUALITY": "NOT_APPLICABLE", "MEANINGFUL_ALPHA_USAGE": "FAIL", "TRANSPARENCY_CAPABILITY": "FAIL"}, notes="ALLOWED still requires a transparency representation and meaningful alpha in 2.0.0a3."),
    FixtureCase("play_icon_wrong_size", "google-play-app-icon", build_play_icon_wrong_size, False, {"TARGET_CONTRACT": "FAIL"}),
    FixtureCase("pwa_maskable_opaque", "pwa-maskable", build_pwa_opaque, True, {"MEANINGFUL_ALPHA_USAGE": "PASS", "EDGE_QUALITY": "NOT_APPLICABLE"}),
    FixtureCase("pwa_maskable_alpha", "pwa-maskable", build_pwa_alpha, False, {"MEANINGFUL_ALPHA_USAGE": "FAIL"}),
    FixtureCase("android_fg_with_alpha", "android-adaptive-foreground", build_android_fg_alpha, True, {"MEANINGFUL_ALPHA_USAGE": "NOT_APPLICABLE", "EDGE_QUALITY": "PASS"}),
    FixtureCase("android_bg_opaque", "android-adaptive-background", build_android_bg_opaque, True, {"MEANINGFUL_ALPHA_USAGE": "PASS", "EDGE_QUALITY": "NOT_APPLICABLE"}),
    FixtureCase("android_bg_with_alpha", "android-adaptive-background", build_android_bg_alpha, False, {"MEANINGFUL_ALPHA_USAGE": "FAIL"}),
    FixtureCase("apple_fg_with_alpha", "apple-icon-foreground", build_apple_fg_alpha, True, {"MEANINGFUL_ALPHA_USAGE": "NOT_APPLICABLE", "EDGE_QUALITY": "PASS"}),
    FixtureCase("apple_bg_opaque", "apple-icon-background", build_apple_bg_opaque, True, {"MEANINGFUL_ALPHA_USAGE": "PASS", "EDGE_QUALITY": "NOT_APPLICABLE"}),
    FixtureCase("truncated_png", "repo-generic", build_truncated, False, {"FILE_IDENTITY": "FAIL"}),
]


def materialize(root: Path) -> list[tuple[FixtureCase, Path]]:
    root.mkdir(parents=True, exist_ok=True)
    out: list[tuple[FixtureCase, Path]] = []
    for case in CASES:
        dest = root / case.output_name()
        path = case.builder(dest)
        out.append((case, path))
    return out

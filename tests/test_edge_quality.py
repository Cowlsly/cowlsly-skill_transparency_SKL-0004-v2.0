from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from transparency_assurance.edge_quality import evaluate_edge_quality
from transparency_assurance.validator import inspect_asset


def _save(tmp_path: Path, name: str, im: Image.Image) -> Path:
    p = tmp_path / name
    im.save(p, "PNG")
    return p


def _subject_circle(size: int = 160, fill=(30, 120, 220, 255), radius: int = 44) -> Image.Image:
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    c = size // 2
    ImageDraw.Draw(im).ellipse((c - radius, c - radius, c + radius, c + radius), fill=fill)
    return im


def test_clean_cutout_passes_edge_quality(tmp_path: Path):
    p = _save(tmp_path, "clean.png", _subject_circle())
    result = evaluate_edge_quality(Image.open(p))
    assert result.status == "PASS"
    assert result.mode == "clean"
    report = inspect_asset(p, "repo-generic")
    assert report["gates"]["EDGE_QUALITY"]["status"] == "PASS"
    assert report["target_compliant"] is True


def test_white_halo_fails_and_is_not_confused_with_a_shadow(tmp_path: Path):
    im = _subject_circle()
    # Thin light-grey fringe around the whole subject, classic knocked-out-on-white matte.
    core = im.split()[-1].point(lambda a: 255 if a >= 250 else 0)
    ring = core.filter(ImageFilter.MaxFilter(5))
    fringe = Image.new("RGBA", im.size, (0, 0, 0, 0))
    for y in range(im.height):
        for x in range(im.width):
            if ring.getpixel((x, y)) == 255 and core.getpixel((x, y)) == 0:
                fringe.putpixel((x, y), (236, 236, 236, 160))
    out = Image.alpha_composite(fringe, im)
    p = _save(tmp_path, "halo.png", out)
    result = evaluate_edge_quality(Image.open(p))
    assert result.status == "FAIL"
    assert result.mode == "halo"
    report = inspect_asset(p, "repo-generic")
    assert report["gates"]["EDGE_QUALITY"]["status"] == "FAIL"
    assert report["target_compliant"] is False
    assert report["capability_state"] == "FAILED_QA_REPAIRABLE"


def test_chroma_spill_fails(tmp_path: Path):
    im = _subject_circle(fill=(30, 80, 210, 255))
    core = im.split()[-1].point(lambda a: 255 if a >= 250 else 0)
    ring = core.filter(ImageFilter.MaxFilter(5))
    fringe = Image.new("RGBA", im.size, (0, 0, 0, 0))
    for y in range(im.height):
        for x in range(im.width):
            if ring.getpixel((x, y)) == 255 and core.getpixel((x, y)) == 0:
                fringe.putpixel((x, y), (40, 220, 50, 180))
    out = Image.alpha_composite(fringe, im)
    p = _save(tmp_path, "spill.png", out)
    result = evaluate_edge_quality(Image.open(p))
    assert result.status == "FAIL"
    assert result.mode == "chroma_spill"
    report = inspect_asset(p, "repo-generic")
    assert report["gates"]["EDGE_QUALITY"]["status"] == "FAIL"
    assert report["target_compliant"] is False


def test_contact_shadow_is_not_treated_as_a_halo(tmp_path: Path):
    size = 180
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    # Soft dark oval sitting below the subject, not wrapping the top.
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse((50, 100, 130, 150), fill=(18, 18, 18, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=6))
    subject = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(subject).ellipse((50, 40, 130, 120), fill=(30, 120, 220, 255))
    out = Image.alpha_composite(shadow, subject)
    p = _save(tmp_path, "shadow.png", out)
    result = evaluate_edge_quality(Image.open(p))
    assert result.status == "PASS"
    assert result.mode == "shadow"
    report = inspect_asset(p, "repo-generic")
    assert report["gates"]["EDGE_QUALITY"]["status"] == "PASS"
    assert report["target_compliant"] is True


def test_subject_tinted_glow_is_not_a_matte_halo(tmp_path: Path):
    size = 180
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
    # Broad soft bloom in the same hue as the subject.
    for radius, alpha in ((70, 30), (62, 60), (54, 100), (48, 150)):
        d.ellipse((90 - radius, 90 - radius, 90 + radius, 90 + radius), fill=(40, 130, 230, alpha))
    subject = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(subject).ellipse((50, 50, 130, 130), fill=(30, 120, 220, 255))
    out = Image.alpha_composite(glow, subject)
    p = _save(tmp_path, "glow.png", out)
    result = evaluate_edge_quality(Image.open(p))
    assert result.status == "PASS"
    assert result.mode == "glow"
    report = inspect_asset(p, "repo-generic")
    assert report["gates"]["EDGE_QUALITY"]["status"] == "PASS"


def test_hair_strands_are_not_treated_as_edge_corruption(tmp_path: Path):
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
    p = _save(tmp_path, "hair.png", im)
    result = evaluate_edge_quality(Image.open(p))
    assert result.status == "PASS"
    assert result.mode == "hair_fur"
    report = inspect_asset(p, "repo-generic")
    assert report["gates"]["EDGE_QUALITY"]["status"] == "PASS"


def test_interior_translucency_is_not_a_halo(tmp_path: Path):
    im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((30, 30, 130, 130), radius=18, fill=(186, 220, 240, 96))
    p = _save(tmp_path, "glass.png", im)
    result = evaluate_edge_quality(Image.open(p))
    assert result.status == "PASS"
    assert result.mode == "translucency"
    report = inspect_asset(p, "repo-generic")
    assert report["gates"]["EDGE_QUALITY"]["status"] == "PASS"


def test_opaque_forbidden_profile_skips_edge_quality(tmp_path: Path):
    p = _save(tmp_path, "feature.png", Image.new("RGB", (1024, 500), (30, 40, 50)))
    result = evaluate_edge_quality(Image.open(p), transparency_forbidden=True)
    assert result.status == "NOT_APPLICABLE"
    report = inspect_asset(p, "google-play-feature-graphic")
    assert report["gates"]["EDGE_QUALITY"]["status"] == "NOT_APPLICABLE"
    assert report["target_compliant"] is True

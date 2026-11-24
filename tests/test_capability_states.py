from pathlib import Path

import pytest
from PIL import Image

from transparency_assurance.cli import main
from transparency_assurance.profiles import PROFILES, AssetProfile, TransparencyPolicy
from transparency_assurance.validator import inspect_asset, report_without_asset_bytes


def test_missing_file_is_not_a_verified_state(tmp_path: Path):
    report = inspect_asset(tmp_path / "does-not-exist.png", "repo-generic")
    assert report["capability_state"] == "NATIVE_ALPHA_REQUESTED_FILE_NOT_ACCESSIBLE"
    assert report["target_compliant"] is False
    assert not report["capability_state"].startswith("VERIFIED")
    assert report["gates"]["FILE_IDENTITY"]["status"] == "FAIL"


def test_visual_only_preview_never_claims_verification():
    report = report_without_asset_bytes(visual_only=True, profile_name="repo-generic", source_path="preview.png")
    assert report["capability_state"] == "VISUAL_ONLY_NOT_FILE_VERIFIED"
    assert report["target_compliant"] is False
    assert not str(report["capability_state"]).startswith("VERIFIED")
    assert all(gate["status"] == "UNVERIFIED" for gate in report["gates"].values())


def test_unavailable_bytes_without_preview_are_not_verified():
    report = report_without_asset_bytes(visual_only=False, profile_name="repo-generic")
    assert report["capability_state"] == "NATIVE_ALPHA_REQUESTED_FILE_NOT_ACCESSIBLE"
    assert report["target_compliant"] is False
    assert "sha256" not in report


def test_cli_unavailable_visual_only(tmp_path: Path, capsys, monkeypatch):
    out = tmp_path / "qa.json"
    monkeypatch.setattr(
        "sys.argv",
        ["transparency", "unavailable", "--visual-only", "--json", str(out)],
    )
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
    text = capsys.readouterr().out
    assert "VISUAL_ONLY_NOT_FILE_VERIFIED" in text
    assert '"target_compliant": false' in text.lower() or '"target_compliant": false' in text
    assert out.exists()


def test_corrupt_image_is_failed_identity_not_verified(tmp_path: Path):
    p = tmp_path / "truncated.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"not-a-real-image")
    report = inspect_asset(p, "repo-generic")
    assert report["gates"]["FILE_IDENTITY"]["status"] == "FAIL"
    assert report["capability_state"] == "FAILED_QA_REGENERATE"
    assert report["target_compliant"] is False
    assert not report["capability_state"].startswith("VERIFIED")


def test_decompression_bomb_is_failed_identity(tmp_path: Path, monkeypatch):
    p = tmp_path / "large.png"
    Image.new("RGBA", (64, 64), (0, 0, 0, 0)).save(p)
    monkeypatch.setattr("transparency_assurance.validator.MAX_PIXELS", 16)
    report = inspect_asset(p, "repo-generic")
    assert report["gates"]["FILE_IDENTITY"]["status"] == "FAIL"
    assert "Unsafe image dimensions" in report["gates"]["FILE_IDENTITY"]["reason"]
    assert report["capability_state"] == "FAILED_QA_REGENERATE"
    assert report["target_compliant"] is False


def test_nearly_empty_alpha_fails_topology(tmp_path: Path):
    p = tmp_path / "empty.png"
    im = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    im.putpixel((64, 64), (255, 0, 0, 255))
    im.save(p)
    report = inspect_asset(p, "repo-generic")
    assert report["gates"]["ALPHA_TOPOLOGY"]["status"] == "FAIL"
    assert report["gates"]["ALPHA_TOPOLOGY"]["metrics"]["nearly_empty"] is True
    assert report["target_compliant"] is False


def test_border_expectation_failure_is_directly_asserted(tmp_path: Path, monkeypatch):
    profile = AssetProfile(
        name="test-opaque-border",
        transparency=TransparencyPolicy.REQUIRED,
        border_transparency_required=False,
    )
    monkeypatch.setitem(PROFILES, "test-opaque-border", profile)
    p = tmp_path / "open-border.png"
    im = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    from PIL import ImageDraw
    ImageDraw.Draw(im).ellipse((8, 8, 56, 56), fill=(20, 90, 200, 255))
    im.save(p)
    report = inspect_asset(p, "test-opaque-border")
    assert report["gates"]["BORDER_EXPECTATION"]["status"] == "FAIL"
    assert report["target_compliant"] is False

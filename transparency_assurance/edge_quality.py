from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from PIL import Image

from .composite import composite_linear_srgb


@dataclass(frozen=True)
class EdgeQualityResult:
    status: str
    mode: str
    reason: str
    metrics: dict[str, Any]


def _luma(rgb: np.ndarray) -> np.ndarray:
    r = rgb[..., 0].astype(np.float32)
    g = rgb[..., 1].astype(np.float32)
    b = rgb[..., 2].astype(np.float32)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _chroma(rgb: np.ndarray) -> np.ndarray:
    return rgb.max(axis=-1).astype(np.float32) - rgb.min(axis=-1).astype(np.float32)


def _hue_deg(rgb: np.ndarray) -> np.ndarray:
    r = rgb[..., 0].astype(np.float32)
    g = rgb[..., 1].astype(np.float32)
    b = rgb[..., 2].astype(np.float32)
    maxc = np.maximum(np.maximum(r, g), b)
    minc = np.minimum(np.minimum(r, g), b)
    delta = maxc - minc
    hue = np.zeros_like(maxc)
    nonempty = delta > 1e-3
    r_is = nonempty & (maxc == r)
    g_is = nonempty & (maxc == g)
    b_is = nonempty & (maxc == b)
    hue[r_is] = np.mod((g[r_is] - b[r_is]) / delta[r_is], 6.0)
    hue[g_is] = (b[g_is] - r[g_is]) / delta[g_is] + 2.0
    hue[b_is] = (r[b_is] - g[b_is]) / delta[b_is] + 4.0
    return hue * 60.0


def _angdiff(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    d = np.abs(a - b) % 360.0
    return np.minimum(d, 360.0 - d)


def _dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return mask.copy()
    h, w = mask.shape
    out = mask.copy()
    ys, xs = np.where(mask)
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dy * dy + dx * dx > radius * radius:
                continue
            yy = ys + dy
            xx = xs + dx
            keep = (yy >= 0) & (yy < h) & (xx >= 0) & (xx < w)
            out[yy[keep], xx[keep]] = True
    return out


def _erode(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return mask.copy()
    return ~_dilate(~mask, radius)

def _strand_metrics(alpha: np.ndarray, y0: int, y1: int, x0: int, x1: int) -> tuple[float, float, float]:
    """Return (thin_fraction, transition_density, hair_score) from the binary alpha mask."""
    h, w = alpha.shape
    binary = alpha >= 128
    # Opening with radius 2 keeps a compact body and drops 1-2px strands.
    body = _dilate(_erode(binary, 2), 2)
    strands = binary & ~body
    thin_fraction = float(strands.sum()) / max(1, int(binary.sum()))
    pad = 2
    y0e, y1e = max(0, y0 - pad), min(h, y1 + 1 + pad)
    x0e, x1e = max(0, x0 - pad), min(w, x1 + 1 + pad)
    region = (alpha[y0e:y1e, x0e:x1e] >= 128).astype(np.int16)
    trans = 0
    if region.shape[1] > 1:
        trans += int(np.sum(np.abs(np.diff(region, axis=1)) > 0))
    if region.shape[0] > 1:
        trans += int(np.sum(np.abs(np.diff(region, axis=0)) > 0))
    bbox_area = max(1, (y1e - y0e) * (x1e - x0e))
    transition_density = trans / bbox_area
    hair_score = min(1.0, thin_fraction * 5.0 + transition_density * 10.0)
    return thin_fraction, transition_density, hair_score




def evaluate_edge_quality(image: Image.Image, *, transparency_forbidden: bool = False) -> EdgeQualityResult:
    """Classify edge structure into defect vs legitimate material modes.

    Defects (FAIL): thin white/grey matte halos and chroma spill.
    Legitimate (PASS): clean cutouts, contact shadows, glow, hair/fur, glass/smoke.
    Semantic intent is still UNVERIFIED elsewhere; this gate only grades edge structure.
    """
    rgba = np.asarray(image.convert("RGBA"), dtype=np.uint8)
    rgb = rgba[:, :, :3]
    alpha = rgba[:, :, 3]
    h, w = alpha.shape

    empty_metrics: dict[str, Any] = {
        "edge_mode": "none",
        "halo_score": 0.0,
        "spill_score": 0.0,
        "shadow_score": 0.0,
        "glow_score": 0.0,
        "hair_score": 0.0,
        "translucency_score": 0.0,
        "wrap_sides": 0,
    }

    if transparency_forbidden or int(alpha.min()) == 255:
        return EdgeQualityResult(
            "NOT_APPLICABLE",
            "none",
            "No transparent edge to grade for this asset or profile",
            empty_metrics,
        )

    visible = alpha > 0
    if int(visible.sum()) < 8:
        return EdgeQualityResult(
            "NOT_APPLICABLE",
            "none",
            "Too little visible coverage to grade edge quality",
            empty_metrics,
        )

    core = alpha >= 250
    soft = (alpha > 0) & (alpha < 250)
    ring = _dilate(core, 3) & ~core & visible
    edge = soft | ring

    # Bounding box used by hair detection even when there is no soft fringe.
    if int(core.sum()):
        ys, xs = np.where(core)
    else:
        ys, xs = np.where(visible)
    y0, y1 = int(ys.min()), int(ys.max())
    x0, x1 = int(xs.min()), int(xs.max())
    thin_fraction, transition_density, hair_score = _strand_metrics(alpha, y0, y1, x0, x1)

    if int(edge.sum()) < 8:
        if hair_score >= 0.35 and thin_fraction >= 0.04:
            return EdgeQualityResult(
                "PASS",
                "hair_fur",
                "High-frequency thin strands are consistent with hair or fur, not a matte halo",
                {**empty_metrics, "edge_mode": "hair_fur", "hair_score": round(hair_score, 4),
                 "thin_strand_fraction": round(thin_fraction, 4),
                 "transition_density": round(transition_density, 4),
                 "edge_pixels": int(edge.sum())},
            )
        return EdgeQualityResult(
            "PASS",
            "clean",
            "Hard cutout with no measurable fringe or soft-edge structure",
            {**empty_metrics, "edge_mode": "clean", "edge_pixels": int(edge.sum()),
             "hair_score": round(hair_score, 4), "thin_strand_fraction": round(thin_fraction, 4)},
        )

    luma = _luma(rgb)
    chroma = _chroma(rgb)
    hue = _hue_deg(rgb)

    # Inward colour: mean of nearby higher-alpha core pixels, else global core mean.
    core_luma = float(luma[core].mean()) if int(core.sum()) else float(luma[visible].mean())
    core_chroma = float(chroma[core].mean()) if int(core.sum()) else float(chroma[visible].mean())
    if int(core.sum()) and float(chroma[core].mean()) > 12:
        core_hue = float(np.median(hue[core]))
    elif float(chroma[visible].mean()) > 12:
        core_hue = float(np.median(hue[visible]))
    else:
        core_hue = None

    ey, ex = np.where(edge)
    # Approximate inward sample by looking toward the bounding-box centre of the core.
    cy, cx = (np.argwhere(core).mean(axis=0) if int(core.sum()) else np.argwhere(visible).mean(axis=0))

    inward_luma = np.full(ey.shape, core_luma, dtype=np.float32)
    inward_hue = np.full(ey.shape, core_hue if core_hue is not None else 0.0, dtype=np.float32)
    inward_chroma = np.full(ey.shape, core_chroma, dtype=np.float32)
    for i, (y, x) in enumerate(zip(ey, ex)):
        # Walk a few pixels toward the subject centre and sample the first core-like pixel.
        vy, vx = float(cy) - y, float(cx) - x
        norm = (vy * vy + vx * vx) ** 0.5 or 1.0
        for step in (1, 2, 3, 4, 5):
            yy = int(round(y + vy / norm * step))
            xx = int(round(x + vx / norm * step))
            if 0 <= yy < h and 0 <= xx < w and alpha[yy, xx] >= max(32, int(alpha[y, x])):
                inward_luma[i] = luma[yy, xx]
                inward_hue[i] = hue[yy, xx]
                inward_chroma[i] = chroma[yy, xx]
                break

    edge_luma = luma[ey, ex]
    edge_chroma = chroma[ey, ex]
    edge_hue = hue[ey, ex]
    brighter = edge_luma > (inward_luma + 28.0)
    neutral = edge_chroma <= 36.0
    high_luma = edge_luma >= 170.0
    halo_votes = brighter & neutral & (high_luma | (edge_luma > inward_luma + 50.0))

    hue_gap = _angdiff(edge_hue, inward_hue)
    colorful = edge_chroma >= 40.0
    inward_colorful = inward_chroma >= 12.0
    spill_votes = colorful & (hue_gap >= 50.0) & (inward_colorful | (core_hue is not None))

    dark = edge_luma <= 70.0
    much_darker = edge_luma < (inward_luma - 25.0)
    shadow_votes = dark & much_darker & (edge_chroma <= 45.0)

    # Side wrap of bright-neutral fringe (halo wraps; shadows usually sit on one side).
    mid_y = (y0 + y1) / 2.0
    mid_x = (x0 + x1) / 2.0
    sides = {
        "top": ey < mid_y - 0.15 * max(1, y1 - y0),
        "bottom": ey > mid_y + 0.15 * max(1, y1 - y0),
        "left": ex < mid_x - 0.15 * max(1, x1 - x0),
        "right": ex > mid_x + 0.15 * max(1, x1 - x0),
    }
    wrap_sides = sum(int(np.mean(halo_votes & mask) >= 0.08) for mask in sides.values() if int(mask.sum()) >= 4)

    # Falloff width: how far partial alpha extends beyond the hard core.
    if int(core.sum()) and int(soft.sum()):
        # Distance transform approximation: dilation radius until most soft pixels are covered.
        falloff_px = 0
        covered = core.copy()
        remaining = int(soft.sum())
        for radius in range(1, 17):
            covered = _dilate(core, radius)
            leftover = int((soft & ~covered).sum())
            falloff_px = radius
            if leftover <= 0.08 * remaining:
                break
    else:
        falloff_px = 1 if int(soft.sum()) else 0

    subject_tinted = (edge_chroma >= 16.0) & (hue_gap <= 35.0)
    # Soft bloom can be dim at the outer radius; do not require near-white luma.
    glow_votes = (falloff_px >= 5) & (~dark) & (subject_tinted | ((edge_luma >= 80.0) & (edge_chroma <= 50.0)))

    # Interior translucency: the body itself is mid-alpha, not merely a soft surround.
    interior = _erode(visible, 4)
    if int(interior.sum()) >= 16:
        interior_partial = float(np.mean((alpha[interior] > 16) & (alpha[interior] < 240)))
        interior_core = float(np.mean(alpha[interior] >= 250))
    else:
        interior_partial = 0.0
        interior_core = float(np.mean(core)) if int(visible.sum()) else 0.0

    n_edge = max(1, int(edge.sum()))
    halo_score = float(np.mean(halo_votes))
    spill_score = float(np.mean(spill_votes))
    shadow_score = float(np.mean(shadow_votes))
    # Bottom bias makes a true contact shadow more likely.
    bottom_bias = float(np.mean(shadow_votes & sides["bottom"])) if int(sides["bottom"].sum()) else 0.0
    if bottom_bias >= 0.08 and wrap_sides <= 1:
        shadow_score = min(1.0, shadow_score + 0.25)
    soft_wrap_sides = sum(int(np.mean(mask) >= 0.08) for mask in sides.values() if int(mask.sum()) >= 4)
    glow_score = float(np.mean(glow_votes)) if falloff_px >= 5 and soft_wrap_sides >= 3 else 0.0
    translucency_score = float(interior_partial) if interior_core < 0.25 else 0.0

    # Composite-on-black ring luma supports halo vs shadow.
    black = np.asarray(composite_linear_srgb(image, (0, 0, 0)))
    black_luma = _luma(black)
    if int(ring.sum()):
        ring_black_luma = float(black_luma[ring].mean())
        ring_black_chroma = float(_chroma(black)[ring].mean())
    else:
        ring_black_luma = 0.0
        ring_black_chroma = 0.0
    if ring_black_luma >= 55.0 and ring_black_chroma <= 40.0 and falloff_px <= 4:
        halo_score = max(halo_score, 0.55)

    metrics: dict[str, Any] = {
        "edge_pixels": n_edge,
        "halo_score": round(halo_score, 4),
        "spill_score": round(spill_score, 4),
        "shadow_score": round(shadow_score, 4),
        "glow_score": round(glow_score, 4),
        "hair_score": round(hair_score, 4),
        "translucency_score": round(translucency_score, 4),
        "wrap_sides": int(wrap_sides),
        "falloff_px": int(falloff_px),
        "thin_strand_fraction": round(thin_fraction, 4),
        "transition_density": round(transition_density, 4),
        "ring_black_luma": round(ring_black_luma, 2),
        "core_luma": round(core_luma, 2),
        "interior_core": round(interior_core, 4),
        "soft_wrap_sides": int(soft_wrap_sides),
    }

    # Classification is conservative on defects: minimize false acceptance of halos/spill.
    # A translucent body (glass/smoke) must be recognised before fringe-colour tests,
    # because there is often no opaque core to compare an inward hue against.
    if translucency_score >= 0.50 and interior_core < 0.25:
        return EdgeQualityResult(
            "PASS",
            "translucency",
            "Interior partial alpha is consistent with glass, smoke or other translucency",
            {**metrics, "edge_mode": "translucency"},
        )

    strong_halo = halo_score >= 0.22 and wrap_sides >= 2 and falloff_px <= 5
    # Thin near-white ring even without full wrap still fails if the black composite shows it.
    thin_white_halo = halo_score >= 0.28 and falloff_px <= 4 and ring_black_luma >= 50.0
    strong_spill = spill_score >= 0.20 and hair_score < 0.45 and interior_core >= 0.2

    if (strong_halo or thin_white_halo) and not (glow_score >= 0.35 and falloff_px >= 6):
        return EdgeQualityResult(
            "FAIL",
            "halo",
            "White/grey matte halo detected on the subject edge",
            {**metrics, "edge_mode": "halo"},
        )

    if strong_spill:
        return EdgeQualityResult(
            "FAIL",
            "chroma_spill",
            "Chroma spill detected: edge hue diverges from the inward subject colour",
            {**metrics, "edge_mode": "chroma_spill"},
        )

    if hair_score >= 0.35 and thin_fraction >= 0.04:
        return EdgeQualityResult(
            "PASS",
            "hair_fur",
            "High-frequency thin strands are consistent with hair or fur, not a matte halo",
            {**metrics, "edge_mode": "hair_fur"},
        )

    if shadow_score >= 0.18 and wrap_sides <= 1 and halo_score < 0.22:
        return EdgeQualityResult(
            "PASS",
            "shadow",
            "Dark, low-chroma, side-biased falloff is consistent with a legitimate contact shadow",
            {**metrics, "edge_mode": "shadow"},
        )

    if glow_score >= 0.20 and falloff_px >= 5:
        return EdgeQualityResult(
            "PASS",
            "glow",
            "Broad soft bloom is consistent with glow rather than a thin white/grey matte halo",
            {**metrics, "edge_mode": "glow"},
        )

    if halo_score >= 0.22 or (ring_black_luma >= 60.0 and falloff_px <= 3):
        # Ambiguous but brighter-than-subject neutral fringe: fail closed.
        return EdgeQualityResult(
            "FAIL",
            "halo",
            "Ambiguous bright-neutral fringe treated as a matte halo to avoid false acceptance",
            {**metrics, "edge_mode": "halo"},
        )

    return EdgeQualityResult(
        "PASS",
        "clean",
        "Edges match the subject colour without a wrapping white/grey halo or chroma spill",
        {**metrics, "edge_mode": "clean"},
    )

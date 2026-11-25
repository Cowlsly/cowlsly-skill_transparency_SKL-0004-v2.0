# Changelog

## 2.0.0-alpha.4

### Added
- Deterministic 34-case synthetic fixture corpus (`tests/fixtures/corpus.py`) with parametrized regression coverage for clean cutouts, known failure modes, legitimate edge structure, and built-in target profiles.
- Pinned dependency lockfiles: `requirements.lock` and `requirements-dev.lock`, compiled with `uv pip compile` for Python 3.12. CI now installs from the dev lockfile.

### Still experimental
- Semantic visual grading.
- APNG/frame-aware validation and richer PNG source-representation reporting.
- A measured false-acceptance benchmark on a held-out/generated challenge suite.
- EXIF/XMP policy and animation-aware alpha (remaining P1).

## 2.0.0-alpha.3

### Added
- Mode-aware `EDGE_QUALITY` gate that distinguishes white/grey matte halos and chroma spill from legitimate contact shadows, glow, hair/fur, and glass/smoke translucency.
- Direct positive and negative regression fixtures for each of those edge modes.
- `report_without_asset_bytes()` and a `transparency unavailable` CLI command for environments where final output bytes cannot be inspected.
- Direct tests for missing files, visual-only previews, corrupt/truncated images, decompression bombs, nearly-empty alpha, and opaque-border contract failures.

### Changed
- `EDGE_QUALITY` is now an active hard gate. A halo or chroma-spill failure makes the asset non-compliant instead of leaving the gate unverified.
- Missing files now report `NATIVE_ALPHA_REQUESTED_FILE_NOT_ACCESSIBLE` rather than `FAILED_QA_REGENERATE`, so the validator never claims a verified or regenerate-after-QA state when bytes were not inspected.
- Package and validator version set to `2.0.0a3`.

### Still experimental
- Semantic visual grading.
- APNG/frame-aware validation.
- Expanded 30–50 fixture corpus and an empirical false-acceptance benchmark.
- PNG source-representation reporting, EXIF/XMP policy, and dependency lockfile (P1).

## 2.0.0-alpha.2

### Added
- Conservative spatial fake-checkerboard detector that ignores RGB hidden beneath fully transparent pixels.
- Direct checkerboard positive/negative regression tests.
- Linear-light sRGB compositing utilities and multi-background QA contact-sheet support.
- CLI `contact-sheet`, `attest`, and `profiles` commands.
- Machine-readable QA attestation JSON schema.
- Target-profile JSON records for Google Play app icons and feature graphics, Android adaptive icon layers, PWA maskable icons, and Apple icon foreground/background layers.

### Changed
- Checkerboard QA is now an active structural gate rather than an unverified placeholder.
- Layer-specific target profiles no longer incorrectly require transparency in every asset.
- Capability states remain conservative when semantic/edge QA is unavailable.

### Still experimental
- Mode-aware halo/chroma-spill grading.
- Semantic visual grading.
- APNG/frame-aware validation.
- Large deterministic fixture corpus and empirical false-acceptance benchmark.

## 2.0.0-alpha.1

Initial Transparency Assurance v2 scaffold.

- Added canonical SKL-0004 v2 workflow.
- Added target-aware asset profiles and transparency policies.
- Added deterministic PNG/alpha validator with machine-readable QA report.
- Added conservative boundary-connected flat-background repair.
- Added CLI entry point.
- Added regression tests and GitHub Actions CI.
- Added security guidance and capability-state model.

This alpha is not yet production-ready.

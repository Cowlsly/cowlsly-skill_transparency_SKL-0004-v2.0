# Deterministic fixture corpus

Synthetic, Cowlsly-created regression fixtures for Transparency Assurance v2. There are no third-party image assets in this directory.

Fixtures are built on demand by `tests/fixtures/corpus.py` (see `CASES`). `tests/test_fixture_corpus.py` materializes each case and asserts the expected profile, compliance, gate statuses, and edge mode.

There are currently 34 cases, covering:

- clean cutouts (RGBA, hard rectangle, LA, palette+`tRNS`, RGB colour-key `tRNS`)
- failure modes (opaque required-alpha, topology noise, nearly empty, baked checkerboard, halo, chroma spill, corrupt PNG, JPEG-without-alpha)
- legitimate soft structure (contact shadow, glow, hair/fur, glass/smoke)
- target profiles (Play icon/feature graphic, PWA maskable, Android/Apple layered icons)

Do not treat this corpus as a measured false-acceptance benchmark. That still needs a held-out/generated challenge suite.

Current validator note: a fully opaque 512×512 Play icon (`play_icon_512_opaque`) fails `TRANSPARENCY_CAPABILITY` and `MEANINGFUL_ALPHA_USAGE` even though the profile policy is `ALLOWED`. That is recorded as expected behaviour of `2.0.0a3`, not as target-contract success.

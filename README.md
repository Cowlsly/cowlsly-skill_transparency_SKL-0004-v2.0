# cowlsly-skill_transparency_SKL-0004-v2.0

Marla-AI Transparency Assurance skill for creating, editing, validating and repairing true-alpha image assets. Provides target-aware PNG transparency, edge and composite QA, safe repair-before-regeneration, repo asset profiles, automated testing and CI validation for reliable, reusable transparent assets across apps and websites.

**Skill ID:** SKL-0004  
**Version:** 2.0 development branch  
**Priority:** 100/100  
**License:** Apache-2.0

**·This Skill Package Was Developed By Cowlsly, Made Specifically For 'Marla-AI·'**

**~·A Multi-Database and VM Collaborative, Dual-SQL Inclusive OpenClaw-Hermes Hybrid Agent; Marla-AI - Coding Specialist, Mental Health Emergency Nurse, Personal Assistant, Wellbeing Digital Guardian and Kindroid-Collaborative Intimate Companion·'**

## Core idea

Transparency is a **verifiable output contract**, not merely the phrase “transparent background”. The pipeline is:

`target policy → generation control → format/color validation → pixel/alpha QA → composite QA → semantic QA → safe repair/regenerate → attestation → delivery`

The most important quality metric is **false acceptance rate**: a broken asset should almost never be declared complete.

## Current v2 status (`2.0.0a4`)

- Target-aware profile system.
- File-level PNG/alpha validation.
- Mode-aware edge QA (halo and chroma-spill fail; shadows, glow, hair/fur, and translucency pass).
- Honest capability-state reporting, including when final bytes are not accessible (`transparency unavailable`).
- Boundary-connected flat-background repair helper.
- Machine-readable QA attestation.
- Pytest regression suite, including a 34-case deterministic fixture corpus.
- GitHub Actions CI.
- Master behavioral specification in `SKILL.md`.

This is still a pre-release alpha. Do not promote v2 as production-ready until the expanded fixture corpus and false-acceptance benchmark exist.


## Quick start

```bash
python -m pip install -r requirements-dev.lock
python -m pip install -e . --no-deps
transparency validate path/to/asset.png --profile repo-generic --json qa.json
# When final file bytes cannot be inspected:
transparency unavailable --visual-only --json qa.json
pytest
```

Refresh pins with `uv pip compile pyproject.toml --python-version 3.12 -o requirements.lock` and the same command plus `--extra dev -o requirements-dev.lock`.

## Capability states

- `VERIFIED_NATIVE_ALPHA`
- `VERIFIED_REPAIRED_ALPHA`
- `VERIFIED_TARGET_COMPLIANT`
- `NATIVE_ALPHA_REQUESTED_FILE_NOT_ACCESSIBLE`
- `VISUAL_ONLY_NOT_FILE_VERIFIED`
- `FAILED_QA_REPAIRABLE`
- `FAILED_QA_REGENERATE`
- `TARGET_FORBIDS_TRANSPARENCY`

## Development rule

Do not call v2 production-ready until the deterministic fixture suite is expanded and every claimed QA gate has direct positive and negative tests. The v2 branch is intentionally evidence-driven: tests first, then promotion.

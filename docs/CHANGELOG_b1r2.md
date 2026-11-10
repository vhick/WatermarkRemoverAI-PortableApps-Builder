# WatermarkRemover-AI PortableApps Builder b1r2 — NSIS path-length fix

## Observed failure (user's GitHub Actions run 42742294498, 10 Nov 2026)

The app and launcher's hosted Windows smoke checks passed, and the complete upstream CPU app was ZIP-validated with SHA-256:

`3964dc524ec9da3b8d664f0a2b12f516bd50ede7cf3e9f82e24d535577582c13`

Shared NSIS `makensis.exe` failed while embedding the required PySide6 Qt DLL:

`File: failed opening file ...PySide6\qml\Qt5Compat\GraphicalEffects\private\qtgraphicaleffectsprivateplugin.dll`

Full source path under the caller's GitHub workspace: 261 characters. This exceeds classic Windows MAX_PATH. The pinned shared Package Builder v1.0.0 uses `File /r` to embed the complete App subtree. Its own action contract allows an **absolute** source-dir outside the repository.

The failure is in **installer compilation**, not the app DLL, compiled root launcher, upstream download, profile redirection, or independently validated ZIP. The workflow correctly published a ZIP-only release and then returned failed status.

## b1r2 fix

- Change the full build's post-smoke-test ZIP extraction from long `work/install-stage` to short `$RUNNER_TEMP\w` (only installer input). The validated original ZIP is preserved unchanged.
- Pass `${{ runner.temp }}\w\WatermarkRemoverAIPortable` to the pinned shared NSIS Package Builder as an absolute source path.
- Apply the same short stage to the packaging-only workflow.
- Add `scripts/check_nsis_paths.py` to reject overly long paths early (245-character conservative budget); never omit bundled PySide6 binaries or change Windows global long-path configuration.
- Accept trusted b1r1 and b1r2 ZIP-only releases in packaging-only mode. Extract the checksum-verified original ZIP directly to the short path; preserve its original package revision and publish to the corresponding full release tag. A b1r1 recovery makes a b1r1 installer for the unchanged b1r1 ZIP. Future new full builds use b1r2.
- Add four focused regression tests for short/long paths, accepted prior revision tags, and both workflow stage locations.

## Best path for the failed run

1. Commit this complete b1r2 kit over the original builder repo (do not delete existing releases or modify Data).
2. Actions → **WatermarkRemover-AI - Installer Only from Validated ZIP** → Run workflow.
3. Enter `portable-wmrai-v0.68.0-553b9bcfc2-b1r1-ziponly`.
4. The workflow re-downloads the previously validated ZIP from the **same** repository, verifies its `SHA256SUMS.txt` and internal version/commit/package revision, extracts to the shorter staging directory, checks path budgets, invokes the pinned installer builder, then dry-runs and publishes through the pinned release publisher. No upstream source build or fresh upstream download is performed.
5. The expected successful target release tag is `portable-wmrai-v0.68.0-553b9bcfc2-b1r1` with unchanged original b1r1 ZIP and new `custom-nsis-b1r1.paf.exe` installer.

## Verification status

- Source/log comparison and pinned action interface: SOURCE-INSPECTED.
- Revised scripts: STATIC-VALIDATED, Python syntax compiled.
- Focused regression suite + prior tests: STATIC-VALIDATED (15 local Python tests passed).
- Workflow YAML: STATIC-VALIDATED locally with PyYAML.
- Changed Windows NSIS invocation: NOT YET VERIFIED on hosted Windows after b1r2 commit.
- Actual installer install/reinstall/upgrade/relocation and interactive desktop/model inference: NOT YET VERIFIED.

No host profile, registry, shell entry, application binary, or model/cache data is removed or moved by this fix.

**Commit summary:** `Fix NSIS MAX_PATH failure: short temp staging, early path budget checks, and reusable b1r1 ZIP-only packaging recovery`

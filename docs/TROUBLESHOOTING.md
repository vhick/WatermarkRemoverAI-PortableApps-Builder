# Troubleshooting and safe recovery

| Symptom | Cause / safe action |
|---|---|
| No Actions workflow visible | Ensure `.github/workflows/*.yml` is **in repo root**, committed and pushed to the **default branch**. Reload Actions and ensure workflow access is enabled. |
| 404 for an explicit release | Confirm a stable published tag such as `v0.68.0` exists. An expected nonexistent version is rejected, not silently replaced with main. |
| GitHub 403 / rate limits | The resolver uses only the caller's built-in `GITHUB_TOKEN` for GitHub API metadata. Confirm Actions read access and retry after rate-limit reset. Do not add unnecessary personal access tokens. |
| Official checksum mismatch | Upstream release asset or checksum has changed, download was corrupt, or there is interference. **Stop.** Do not disable SHA-256. Check the official release notes, not a mirror. |
| Source commit mismatch | Upstream release ZIP metadata differs from tagged source. **Stop.** Treat as provenance issue, not a normal build warning. |
| Windows compiler missing | The hosted runner must expose the Microsoft .NET Framework x64 `csc.exe` at its default system location. Do not substitute an unsigned downloaded toolchain blindly. |
| Qt `--check` fails | Inspect `Data/desktop.log` and runner log. The app may require desktop/Qt capability not available in that particular runner. Do **not** classify a successful static build as functional GUI verification; use real Windows acceptance. |
| Models fail | Open Models > Download / Retry. Check available space, HTTPS connectivity to GitHub and Hugging Face, and any antivirus/network controls. Keep partial models under Data; never delete user downloads blindly. |
| Silent output videos | Upstream requires FFmpeg on PATH to preserve audio. Supply an approved copy separately; do not assume the builder includes it. |
| App writes unexpected host state | Identify the exact writer with Process Monitor or reproducible before/after snapshots; differentiate Qt/OS caches from application files. Keep existing data; do not bulk-delete AppData or registry branches. |
| Installer generation fails | For b1r1 `File: failed opening file` with PySide6/Qt, the failing path was 261 characters; update to builder b1r2 and use installer-only with the pre-existing ZIP-only tag. A short `$RUNNER_TEMP\w` source is used by the fixed workflow. Never delete Qt DLLs. Main workflow marks the installer failed but publishes a SHA-validated ZIP under a `-ziponly` tag when possible. Use **Installer Only from Validated ZIP** with that exact tag to retry the shared NSIS packaging stage without rebuilding/downloads from upstream. |
| Installer won't upgrade | Close the portable app completely, back up `Data`, confirm AppID matches. If `.__UPB_Backup` or `.__UPB_Stage` exists after a failed upgrade, inspect the backed-up files; do not remove the folder casually. |
| Portable folder moved | App caches are resolved relative to the root at launch, but media input/output choices saved in `Data/ui.yml` can be absolute; re-select them after relocation. |
| File cannot be overwritten | Windows locks active binaries. Close all related app windows/workers. Do not force-delete running executable files or change permissions of unrelated profiles. |
| Existing release tag conflict | Publisher protects existing releases. Never overwrite a tag with different bytes; use a newer builder/package revision after modifying the kit. |

## Reverting to the last known good version

1. Fully close the application and its owned workers. Copy the **entire** existing portable tree to backup before changing files.
2. Download the prior known-good ZIP or installer from the builder repository's Releases. Check its `SHA256SUMS.txt`.
3. Prefer extracting the prior version into a **new** directory, not destructively overwriting current `App`.
4. Copy back your preserved **Data** tree in full, including empty folders. Avoid merging files over newer database/config schemas if upstream made breaking changes; restore the version-matched Data backup if necessary.
5. Confirm UI, settings, model hashes and a small test image before cleaning up the old installation. Do not delete unfinished shared-installer backup directories until diagnosed.

## Commit summary for initial upload

`Build D-Ogi WatermarkRemover-AI PortableApps b1r1: verified CPU releases, compiled launcher, portable model/profile paths, source/ZIP checks, Windows runtime fixture, pinned NSIS installer and publisher, ZIP-only recovery, packaging-only workflow`

## b1r2 repair commit summary

`Fix NSIS MAX_PATH failure: restore verified ZIP to short runner-temp stage, preflight all input paths, and support packaging-only recovery of existing b1r1 ZIP-only releases`

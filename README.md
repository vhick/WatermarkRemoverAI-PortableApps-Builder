# WatermarkRemover-AI PortableApps Builder Kit — b1r1

Independent community builder for **D-Ogi/WatermarkRemover-AI**. Mode is **PORTABLEAPPS only**, backend defaults to **CPU-only**, and installer engine is **custom-nsis**. This is **not** a PortableApps.com certified/official installer.

The builder is source code and workflows, **not** the ~470 MiB application binary. When you run its GitHub Actions workflow, it downloads the real official stable Windows release, verifies the release's `SHA256SUMS.txt`, checks the tagged source/commit, compiles `WatermarkRemoverAIPortable.exe` from the included readable C# source, stages the complete PortableApps folder, validates and ZIPs it, restores pristine installer input from the validated ZIP after runtime checks, invokes `vhick/Portable-Package-Builder@v1.0.0`, and publishes through `vhick/portable-release-publisher@v1.1.1`. No upstream fork or local programming tools are required.

## Fast start with GitHub Desktop

1. In **GitHub Desktop**, choose **File > New repository**. Name it `WatermarkRemoverAI-PortableApps-Builder`. This must be a **new builder repo**, not a fork of D-Ogi's repo. Choose private or public; a private release stays in a private repository. GitHub Windows runner usage is charged under the current account rules.
2. Click **Create repository**, then **Repository > Show in Explorer**.
3. Open the builder-kit ZIP that accompanies this README. **Extract its contents into the new repository folder**, so `.github/workflows/build-portableapps.yml` is directly under the repository root. Do not insert an extra nested builder-kit folder. Windows Explorer might hide the `.github` directory; it must be included.
4. Return to GitHub Desktop. Type a summary such as `Add WatermarkRemover-AI PortableApps builder b1r1`, click **Commit to main**, and **Publish repository**. Choose visibility before publishing.
5. Open your GitHub builder repository in your browser. Go to **Actions** > **WatermarkRemover-AI - Build PortableApps ZIP and Installer** > **Run workflow**. Leave `upstream_version=latest` or enter a verified stable version such as `0.68.0`. Leave desktop check enabled for the strongest available headless validation.
6. After it finishes, click the workflow run. Each step shows success/failure and its logs. A failure never proves a portable package exists.
7. If all steps pass, open your builder repository's **Releases** section. Download both `WatermarkRemoverAIPortable_...zip` and its `...paf.exe` installer. The publisher also generates `SHA256SUMS.txt`.
8. **ZIP option:** fully extract the ZIP into a writable drive/folder. Open `WatermarkRemoverAIPortable/WatermarkRemoverAIPortable.exe`. **Installer option:** run the `.paf.exe` and select your PortableApps location; it is an independent community NSIS installer, *not* the official PortableApps.com tool. Refresh/restart the PortableApps Platform menu if it has not detected the app.
9. Inside the app, open **Models** > **Download / Retry** to fetch roughly 1.8 GB of model files. These downloads are separate from the release ZIP. The CPU build does not use an NVIDIA GPU. FFmpeg must be supplied separately if you want video audio preserved.
10. **Upgrade:** close the application fully and back up **the entire `Data/` directory**, including empty folders and partial model downloads. Reinstall into the same app directory (or extract into a new one and copy the full `Data/` directory), without overwriting it. Keep the old version until new processing works. **Rollback:** close the new app and return to the previous App/Other/launcher with the backup `Data`; watch for potential newer data formats.

### PortableApps package tree after a successful run

```text
WatermarkRemoverAIPortable/
  WatermarkRemoverAIPortable.exe        # REAL compiled C# Windows PE launcher
  App/
    AppInfo/
      appinfo.ini
      appicon.ico
      appicon_16.png
      appicon_32.png
    WatermarkRemoverAI/
      WatermarkRemover-AI.exe           # untouched official upstream launcher
      python/                          # bundled Python / PySide6 / AI runtime
      desktop_main.py, ui/, models/ etc
      LICENSE and dependency notices
  Data/                                # portable settings, logs, model downloads
  Other/
    Source/                            # readable launcher and build provenance
  README.txt
```

**Always start the root `WatermarkRemoverAIPortable.exe`.** Running the original app in `App/WatermarkRemoverAI` directly bypasses the portable environment setup and can write data into the app subfolder or host account.

### Two workflows

- **Build PortableApps ZIP and Installer** — downloads and checks the upstream CPU-only archive, compiles the root launcher, validates, packages and publishes. Automatically skips work if a complete release already exists with the same upstream commit and builder revision. If shared NSIS packaging fails after ZIP validation, publishes the validated ZIP **alone** under a clearly labeled `-ziponly` release and marks the run failed.
- **Installer Only from Validated ZIP** — retry packaging from an earlier `-ziponly` release in **this same builder repository**. Enter that exact release tag. Verifies the original ZIP against its `SHA256SUMS.txt`, verifies internal provenance, reuses the unchanged ZIP, builds a new installer via the same pinned action and publishes a full release. **No upstream rebuild**.

### Release identity

Full release tags follow `portable-wmrai-v{upstream_version}-{upstream_commit_first_10}-b1r1`. The ZIP basename is `WatermarkRemoverAIPortable_{version}_cpu_b1r1.zip`; installer filename comes from the **actual shared Package Builder** and ends with `.paf.exe`. Exact SHA-256 hashes are available only after that particular run and are never prefilled in this kit.

The upstream stable release resolver uses numeric `X.Y.Z` ordering and rejects beta/RC/nightly, expected 404 is handled, and genuine API errors fail. Official upstream release asset checksums are mandatory. `identity.json` records the release/tag, full source commit, official ZIP hash, Python runtime manifest identity, requirement hashes and kit revision. Staging requires the upstream ZIP's `build-info.json` to agree with the source tag and commit.

### Default data and portability model

The official upstream uses `WMR_DATA_DIR` before desktop startup. The **compiled root launcher** sets the child process environment to:

- `WMR_DATA_DIR=<portable root>\Data`
- `TORCH_HOME=<Data>\models\torch`
- `HF_HOME=<Data>\models\huggingface`
- `HF_HUB_CACHE` and `HUGGINGFACE_HUB_CACHE` under `Data\models\huggingface\hub`
- `XDG_CACHE_HOME=<Data>\xdg-cache`

The launcher does **not** rewrite system-wide `%TEMP%`, `%APPDATA%`, `%LOCALAPPDATA%`, `%PROGRAMDATA%` or registry settings. It creates only its own `Data` hierarchy (including empty model-cache directories), starts the upstream portable EXE with original arguments, uses a **per-folder** mutex and waits for the upstream launcher to exit. A moved drive/folder recalculates portable paths at runtime. The upstream app retains responsibility for its PyWebview/Qt child-process shutdown.

The builder deliberately does not implement speculative cleanup of Windows shell/Qt data or unrelated files. Inspect the application-specific audit in `docs/AUDIT_AND_VALIDATION.md` for what is grounded by source, and what still needs real Windows observations.

### Security, licensing, limits

- The root launcher is a real **unsigned** compiled Windows PE, not an encoded script. It is produced on GitHub's Windows runner; the kit itself contains only its readable source.
- Official upstream application code is MIT licensed; the upstream archive also includes LGPL/Qt/Python/PyTorch and other third-party notices. Do not redistribute model weights without checking their separate terms. The original community launcher icon in this kit is an independently drawn illustration, not D-Ogi's mark.
- No installer elevation, services, drivers, startup shortcuts or file associations are requested. Windows manages its own recent-file, shell and security caches; this kit does not promise zero OS activity.
- This builder is **CPU-only by design**. The upstream GPU+CPU archive is approximately 1.68 GiB compressed and adds size, driver, and installer limitations. Running the CPU package on a machine with an NVIDIA GPU does not automatically turn it into a CUDA build.
- `--check` is the real upstream Qt GUI/bridge diagnostic. It is not a substitute for first-download, media processing, CUDA, device migration, notification, or installer install/upgrade tests on your own Windows system.
- To prevent a future action-version change from going unnoticed, `scripts/check_actions.py` verifies the known pinned `action.yml` input/output interfaces. The workflow uses exactly the requested action **tags**; a full immutable commit SHA has **not** been independently established for those two pinned tags in this session.

See `docs/AUDIT_AND_VALIDATION.md`, `docs/WINDOWS_ACCEPTANCE.md`, `docs/TROUBLESHOOTING.md`, and `licenses/ATTRIBUTION.md` before considering portability fully validated.

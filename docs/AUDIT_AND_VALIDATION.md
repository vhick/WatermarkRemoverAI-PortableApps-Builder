# Source audit, architecture, and verification — b1r1

## Resolved mode

**PORTABLEAPPS only.** The official stable D-Ogi Windows CPU archive provides a compiled upstream desktop EXE, full embedded CPython runtime, PySide6 / Qt WebEngine, application source, and license notices. It is an on-demand desktop utility. It is **not** a NATIVE architecture project and no native source-built EXE product is offered.

## Exact inspected upstream baseline

- Repo: `https://github.com/D-Ogi/WatermarkRemover-AI`
- Latest verified release on 2026-11-10: `v0.68.0`
- Source SHA stated in release notes: `553b9bcfc29ebfc9e7b2f5779091379be2db8ba1`
- CPU asset: `WatermarkRemover-AI-0.68.0-windows-x64-cpu.zip` (~470 MiB). SHA256SUMS.txt is release-provided; its exact digest is fetched and checked during CI, not guessed here.
- Upstream `desktop_runtime.py` reads `WMR_DATA_DIR`, then `portable.flag`, then `%LOCALAPPDATA%/WatermarkRemover-AI`. It sets Torch/Hugging Face cache variables when `portable.flag` is present and configures `desktop.log`.
- `desktop_main.py` calls `configure_runtime()` **before** GUI import, `remwmgui.py` stores `ui.yml` at `data_dir()`, `model_assets.py` uses Hugging Face cache variables and verifies Florence downloads, and `lama_inpaint/model_store.py` uses TORCH_HOME and verifies LaMA weights.
- `remwmgui.py` runs PyWebview `gui='qt'` on Windows; preview/processing/model preparation use bounded own child processes. It uses local HTTP assets and a Qt WebEngine browser, which can create OS-managed caches outside Python's `data_dir()`.
- `packaging/Launcher.cs` is an upstream compiled .NET Framework GUI bootstrapper which launches packaged Python and permits `--check` only. We keep the upstream EXE **unchanged** and add a community compiled root launcher that prepares portable paths before invoking it.
- The upstream releases are not code-signed. Qt/PySide6 are distributed under third-party license terms; models are downloaded separately. FFmpeg is optional and discovered on PATH.
- Source-based build alternative: `scripts/build_windows.py --backend cpu` compiles the upstream EXE and downloads embedded Python and pip/PyTorch. We avoid that expensive, redundant rebuild because the project ships a verified developer portable binary.

## Mode-specific findings

| Finding / evidence | Path / component | PORTABLEAPPS remedy | Data safety and test | Tradeoff / limitation |
|---|---|---|---|---|
| SOURCE-INSPECTED: settings/desktop log | `desktop_runtime.py`, `remwmgui.py`; normally `%LOCALAPPDATA%\WatermarkRemover-AI` when no flag/override | Root launcher sets `WMR_DATA_DIR=Data` *before* source startup | Assert environment with fixture; verify actual `Data/ui.yml`, `Data/desktop.log` manually | Direct-launch upstream EXE bypasses redirection |
| SOURCE-INSPECTED: model stores | `model_assets.py`, `lama_inpaint/model_store.py`; HF_HOME/TORCH_HOME | Set scoped env under `Data/models` | SHA checks provided by upstream; manually test download/retry, nested and fully empty directories | First models ~1.8 GB; CPU-only processing |
| SOURCE-INSPECTED: self-contained runtime | `packaging/Launcher.cs`, `scripts/build_windows.py`, packaged `python/` + `ui/` | Preserve official ZIP's full runtime; validate SOURCE commit and source files | Official SHA256SUMS + `build-info.json` + PE checks | Exact filesystem and third-party license verification requires downloaded asset |
| SOURCE-INSPECTED: worker lifecycle | `desktop_models.py`, `remwmgui.py`, upstream .NET launcher | Wait for upstream GUI process; parent forwards args; no broad process kills | Fixture and actual `--check` in Windows CI; manual child shutdown test | Unknown crashed/orphaned Qt/worker processes need separate live inspection |
| SOURCE-INSPECTED: user-selected inputs/outputs | `remwmgui.py` | Preserve user's chosen external media locations; no migration/deletion | Manual image/video safety tests | User-specified paths intentionally remain outside Data |
| INFERRED, NOT RUNTIME-OBSERVED: Qt WebEngine cache and Windows shell | PyWebview Qt runtime, Windows shell | No unverified `%LOCALAPPDATA%` scavenger or registry cleanup | Before/after evidence collection and manual Windows acceptance | Windows-managed caches/Qt profile traces might remain; cannot promise full zero-trace portability |
| SOURCE-INSPECTED: no source-level explicit Windows startup/service/shell-registration feature identified in inspected files | App and framework | No autostart, shell, COM, Start Menu cleanup or AUMID rewrite added | Manual observation on installed-app coexistence | Framework/OS-generated traces not fully audited on a running Windows desktop |
| SOURCE-INSPECTED: community installer | `vhick/Portable-Package-Builder@v1.0.0` `scripts/build.ps1`, `nsis/community-installer.nsi` | Independent custom NSIS `.paf.exe` after validated ZIP | Static PE output validation, manual install/upgrade | No official PortableApps certification; actual installer behavior not tested here |

No app-specific TraceGuard or ShellGuard currently runs: source-backed direct paths cover known persistent model/settings data, and **no precisely attributable external application-owned files or registry entries have yet been established by live host comparison**. Adding destructive path harvesting without proof would threaten installed applications. A future release may require a narrow adapter if Windows tests reveal a truly app-owned external path.

## Verified action contracts

`vhick/Portable-Package-Builder@v1.0.0` `action.yml`: `source-dir`, `output-dir` required; `engine`, `running-exe`, `timeout-seconds`, `package-revision` optional; `official-tool-url`, `official-tool-sha256` only for official experimental engine. Outputs are `installer-file`, `installer-sha256`, `app-id`, `app-version`. Source code of that pinned tag was inspected for relative path checks, custom-NSIS process invocation, rollback behavior, no embedded Data files and PE validation.

`vhick/portable-release-publisher@v1.1.1` `action.yml`: `files` and `tag` required; `release-title`, `tag-prefix`, `keep-releases`, `prune`, `dry-run` optional. Calling repository GITHUB_TOKEN and `contents:write` permission used. First dry-run true, then false, no pruning, three retained if pruning is later enabled.

**Note on provenance:** both are pinned to **user-requested tags**, not a claimed verified immutable commit. Build logs record exact resolved code through the public tag and interface verification; independently pin full commits if later confirmed by a trusted source.

## Validation evidence as of builder-kit creation

| Test/stage | Status | What it proves / does NOT prove |
|---|---|---|
| Source audit | **SOURCE-INSPECTED** | Code locations and supported env vars above; no live host behavior claimed |
| Kit Python syntax | **STATIC-VALIDATED** | Scripts parse under local Python |
| Kit tests | **STATIC-VALIDATED** | Eleven local tests pass; no downloaded application involved |
| GitHub Actions YAML parse | **STATIC-VALIDATED** | Workflow structure parsed locally; GitHub runtime not exercised |
| Pinned `action.yml` online examination | **SOURCE-INSPECTED** | Inspected actual pinned action input/output declarations |
| Official asset SHA download + extraction | **NOT YET VERIFIED** | Implemented as mandatory CI steps; asset not downloaded locally |
| Compiled root launcher | **NOT YET VERIFIED** | Complete C# code in kit; Windows compiler not available in this session |
| Windows fixture smoke test | **NOT YET VERIFIED** | CI test program included; not executed |
| Actual `--check` GUI / bridge | **NOT YET VERIFIED** | Will run on hosted Windows if input enabled; no model inference proof |
| New/changed/empty directories, crash/relocation | **NOT YET VERIFIED** | Initial empty dirs created; end-to-end manual persistence test needed |
| TraceGuard/ShellGuard | **NOT IMPLEMENTED — NO VERIFIED NEED** | Direct paths preferred; external framework traces unverified |
| Notifications, AUMID, taskbar, Shell cache | **NOT YET VERIFIED** | Must check on real interactive Windows system |
| Installer generation | **NOT YET VERIFIED** | Shared action called only after ZIP validation |
| Actual installer install/upgrade | **NOT YET VERIFIED** | Requires manual Windows acceptance; static PE check alone insufficient |
| Release publication | **NOT YET VERIFIED** | Publisher invocations included; not run in owner's builder repo |

## Upgrade and rollback safety

Keep `Data` completely separate from `App`. Shared NSIS installer is designed to stage and swap its managed `App`, `Other` and root launcher while leaving `Data` untouched. The installer also checks locks and refuses unknown destination identities; however, nested junction behavior and real upgrade execution still require testing. Preserve `.__UPB_Backup` and `.__UPB_Stage` if it reports failure. Never delete them before inspecting backups. Back up `Data` before any upgrade because models may have gigabytes of downloaded or partially-downloaded files.

`Data/ui.yml` can remember absolute user-chosen input/output media paths, which may become stale after moving drives. Choose new paths from within the GUI; do not blindly rewrite unrelated paths or merge with an installed application's profile.

## Sources inspected

- https://github.com/D-Ogi/WatermarkRemover-AI/releases/tag/v0.68.0
- https://raw.githubusercontent.com/D-Ogi/WatermarkRemover-AI/v0.68.0/desktop_runtime.py
- https://raw.githubusercontent.com/D-Ogi/WatermarkRemover-AI/v0.68.0/remwmgui.py
- https://raw.githubusercontent.com/D-Ogi/WatermarkRemover-AI/v0.68.0/model_assets.py
- https://raw.githubusercontent.com/D-Ogi/WatermarkRemover-AI/v0.68.0/lama_inpaint/model_store.py
- https://raw.githubusercontent.com/D-Ogi/WatermarkRemover-AI/v0.68.0/packaging/Launcher.cs
- https://raw.githubusercontent.com/D-Ogi/WatermarkRemover-AI/v0.68.0/scripts/build_windows.py
- https://raw.githubusercontent.com/vhick/Portable-Package-Builder/v1.0.0/action.yml
- https://raw.githubusercontent.com/vhick/Portable-Package-Builder/v1.0.0/scripts/build.ps1
- https://raw.githubusercontent.com/vhick/Portable-Package-Builder/v1.0.0/nsis/community-installer.nsi
- https://raw.githubusercontent.com/vhick/portable-release-publisher/v1.1.1/action.yml

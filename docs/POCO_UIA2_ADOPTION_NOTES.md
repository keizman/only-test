Title: Migrating Airtest IDE’s Poco to UIAutomator2-only — Issues, Root Causes, Fixes

Scope
- Replace legacy UIAutomator1 stack with UIAutomator2 only, while keeping Poco’s API and dump format stable.
- Make it work inside AirtestIDE’s embedded Python 3.6.8 (no site‑packages), without changing IDE internals.

Note on Visual Recognition (Omniparser)
- Current project status: visual recognition (Omniparser) is NOT supported and remains disabled by default.
- Default identification mode is XML (UIAutomator2). Any future re‑enablement will be explicitly documented and gated by configuration.

Major Problems Encountered
- Embedded Python has no pip/site‑packages; imports fail (ImportError: uiautomator2, adbutils, whichcraft, xmltodict, cigam, progress, …).
- Old PIL shipped by IDE (5.4.1) causes crashes in libs expecting newer Pillow (UnidentifiedImageError) or binary core mismatch (_imaging).
- progress package shadowed by an IDE-bundled progress.py(c); ‘progress is not a package’ / ‘no attribute bar’.
- Python 3.6 lacks re.Pattern/re.Match; some libs check for these symbols (3.7+).
- UIAutomator2 looked up its APK assets inside a .whl path; Apk files could not be read from a zip import path.
- Module caching/import order: even after placing correct files, interpreter kept using earlier, wrong modules/paths.

Why Earlier Attempts Failed
- Injecting PYTHONPATH in scripts does not affect Poco driver import path during IDE startup.
- Dropping wheels into a folder without controlling sys.path order led to imports from .whl instead of real folders.
- Mixing Pillow versions in‑process is unsafe (binary core already loaded). Upgrading only part of Pillow caused core/version mismatch.
- progress module name conflict was not handled; Python imported IDE’s progress.py(c) instead of the actual package.
- uiautomator2 assets require file‑system access; loading from a .whl prevented the APK extractor from finding files.

Final Working Fixes
- Third‑party bootstrap in Poco driver:
  - Add vendor paths automatically: <poco>/thirdparty, thirdparty/site-packages, thirdparty/whl.
  - Log added paths when POCO_THIRDPARTY_DEBUG=1.
- Eliminate Pillow conflicts:
  - Remove all Pillow files from vendor folder; rely on IDE’s built‑in PIL 5.4.1.
  - Shim PIL.UnidentifiedImageError when missing.
- Provide Python 3.6 shims:
  - Define re.Pattern and re.Match using compiled pattern/match types.
- Resolve progress shadowing:
  - If a flat progress module is present, purge it and prefer the package under vendor site‑packages.
  - Fallback shim for progress.bar.Bar when package is unavailable.
- Force uiautomator2 to load from extracted files, not .whl:
  - Extract uiautomator2 wheel into thirdparty/site-packages/uiautomator2 (ensure assets/ contains the APKs).
  - Do not add any uiautomator2-*.whl to sys.path; remove uiautomator2 whl paths if present.
  - If uiautomator2 was imported from a .whl, unload uiautomator2* from sys.modules and re‑import.
- Fill missing deps in vendor site‑packages:
  - adbutils, apkutils2 (sdist extracted), whichcraft, xmltodict, cigam, progress.

Operational Notes
- One‑time device init outside IDE is still recommended: python -m uiautomator2 init.
- Prefer file‑based packages over .whl when libraries need bundled assets.
- Always print module __file__ during debug to confirm source.
- Keep vendor libs minimal; avoid duplicating system libs that IDE already ships, unless strictly necessary.

Verification Outcomes
- UIAutomator2 connects and dumps hierarchy; package attribute is preserved end‑to‑end.
- No visibility filtering; overlays/video playback elements are present in dumps.
- Actions (click, long_click, set_text) compatible with existing Poco scripts.

Key Takeaways
- Embedded environments require deterministic sys.path control and module cache management.
- When assets are involved, never import a library from a zip/whl path.
- Provide small, targeted compatibility shims rather than upgrading large platform components in‑process.

Recent Issues and Fixes (Appendix)

1) UIA2 assets not found (apk install failures)
- Symptom: file '…/uiautomator2-…whl/uiautomator2/assets/app-uiautomator.apk' not found; repeated install attempts.
- Root cause: uiautomator2 was imported from the wheel path; assets are not accessible via zip imports.
- Fix:
  - Extract uiautomator2 wheel into thirdparty/site-packages/uiautomator2.
  - Never add uiautomator2-*.whl to sys.path; strip any existing entries.
  - If uiautomator2 already imported from a wheel, unload uiautomator2* from sys.modules and re-import.
  - Add warning output “uiautomator2 loaded from: …” for verification.

2) Dependency chain breakages under embedded Python
- Symptoms: ImportError: whichcraft/xmltodict/cigam/adbutils/apkutils2/progress; or ‘progress is not a package’.
- Root causes:
  - No site-packages; missing vendorized libs.
  - progress module name collision with IDE’s internal progress.py(c).
- Fix:
  - Vendorize missing packages in thirdparty/site-packages; for sdist (apkutils2/progress) extract and copy package folder.
  - Before UIA2 import: purge flat ‘progress’ module; prefer real package in vendor path; final shim for progress.bar.Bar if needed.
  - One‑click installer scripts added: tmp/poco/setup_airtest_uia2_deps.ps1/.bat to re-populate vendor libs from PyPI.

3) Pillow core/version mismatch; UnidentifiedImageError missing
- Symptoms: _imaging built for 5.4.1; import error for UnidentifiedImageError.
- Root cause: IDE’s old PIL core loaded first; wheel-based Pillow caused mixed versions.
- Fix:
  - Do not vendor Pillow; rely on IDE’s PIL.
  - Shim PIL.UnidentifiedImageError when missing to satisfy UIA2 imports.

4) Coordinate drift (lower screen offset)
- Symptom: Element highlights consistently low; e.g., required y+∆ to select.
- Observations on device: device.info displayHeight=2441, window_size/screenshot=2560; XML width/height absent.
- Root cause: Normalization used displayHeight (2441) while overlay drew against screenshot (2560).
- Fix evolution:
  - Tried XML width/height (sometimes missing/varies); still mismatched overlay.
  - Final: Normalize using device.window_size() as authoritative basis; fallback to device.info only if needed.
  - Wire dumper.get_screen_size() through Input/Screen/Helpers to keep a single source of truth.

5) Playback overlay controls missing in dump
- Symptom: Fullscreen video controls not present in UI tree; older build showed them (with minor offset).
- Root cause: Compressed hierarchy omits overlay views on some OEMs.
- Fix:
  - Dump uncompressed hierarchy: device.dump_hierarchy(compressed=False) with safe fallbacks.
  - Keep visibility filtering disabled to retain controls marked not visible-to-user.

6) Path order and debugability
- Added POCO_THIRDPARTY_DEBUG=1 to log added vendor paths and write to thirdparty/_debug_paths.txt.
- Emitted import-source warnings to confirm file-based packages are used.

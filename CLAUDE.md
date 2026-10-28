# merge-classes

GUI transform app: images project → new project `<name>(merged classes)` in the same workspace with the
classes the user picked merged into another class (or all classes into one). `FIXES.md` has the
behaviour contract, the fixes and the intentional changes versus the pre-2026-10 (AppService) version.

- Entry: `uvicorn src.main:app` (`config.json` `entrypoint`); modules import each other as `src.*`.
  `src/main.py` is the composition root (env → Api → GUI); creating `app` at import is required by uvicorn.
- `src/ui.py` (`MergeClassesGui`): widgets + Run handler; platform side effects arrive as callbacks from
  `main.py` (merge, set task output / workflow / `app.stop()`).
- `src/merger.py` orchestrates the copy (reads the current meta, validates the mapping, dataset tree incl.
  nested, batches of 50); `src/platform_io.py` is the only module calling the API; `src/core/merge.py` is
  the pure logic (targets, validation, destination meta, label reassignment, keypoint node remapping).

Runtime: bare `supervisely/base-py-sdk-hardened:<sdk>` (Python 3.14), no per-app image because
`dev_requirements.txt` holds only the SDK. SDK must stay within the range `supervisely/versions.json`
allows for `instance_version`.

Keep: `config.json` `name`/`context_menu`, the result name suffix and project description
`(merged classes)`, the warning "Please, define at least one transformation", and that the source
project is only read.

Gotchas: `ProjectThumbnail` crashes on a project without images (`_thumbnail_info` guards it).
`app.stop()` sends SIGINT to the process, so never call the real `finished` callback in tests.

Tests: `pytest` (unit, offline; the GUI through `Application.test_client`, the copy against a fake API).

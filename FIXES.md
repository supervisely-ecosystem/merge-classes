# merge-classes: fixes 2026-10

Branch `ecosystem-fixes-2026-10` from `origin/master` @ bf30c28 (v1.3.7). Lifecycle `legacy`, 1,998 runs.
Fixes first on the old code (each with a test that fails before it), then a rewrite on `sly.Application`
widgets because the image move is not possible on the AppService runtime (see "Image").

## Behaviour contract

**Entry.** Context menu of an images project → Run App → Transform → Merge classes. GUI session
(`task_location: workspace_tasks`, `isolate: true`). The modal (`src/modal.html`) is informational only; the
project arrives as `modal.state.slyProjectId`. No other modal state. Non-images projects are rejected.

**GUI.**
- Input card (source project), Output card (Run, progress, result project).
- "Merge classes" card:
  - checkbox "Merge all classes into one" and, when ticked, a class select: every class goes to the
    chosen one;
  - otherwise one row per class (sorted by name): `remain unchanged` + the classes it can be merged into
    (same shape; keypoints only with the same node labels); a class with no candidates has a disabled
    select.
- Run with nothing to do → warning "Please, define at least one transformation", nothing is created.

**Output.**
- A new images project `<source name>(merged classes)` (suffix not repeated; the platform adds `_001`… on
  conflicts) in the source workspace, description `(merged classes)`.
- Meta = source meta without the merged-away classes. The destination classes are unchanged. Tag metas
  are kept, and tags limited to a merged-away class are now limited to its destination.
- Same dataset tree (nested included), images added by id with names and image meta.
- Annotations: objects of a merged class move to the destination class and keep their geometry, tags,
  description and binding key. Keypoints are remapped node by node by node label. Other objects and image
  tags are copied as is.
- Task output = new project; workflow: source project in, new project out; the session stops by itself.
- The source project is only read.

## Findings

### Fixed (one commit each, offline tests)

| Commit | Fix | Tests (old → new) |
|---|---|---|
| ca304a1 | Extract pure logic into `src/core/merge.py`, no behaviour change | 0 → 7 |
| 9dfd767 | Merged keypoint objects lost their tags, description and binding (rebuilt as a bare `Label`) | 7 → 8 (new test fails on old: tags `[]`) |
| dffccaf | Impossible merges crashed mid-copy and left a half-filled result: "Merge all" across shapes (`RuntimeError: Input geometry type Rectangle != … Polygon`), keypoints with other node labels, keypoints → `any`. Now checked before anything is created; error dialog lists the classes | 8 → 12 (4 new fail on old) |
| 8e65901 | Tags limited to a merged-away class still pointed at the deleted class | 12 → 13 (`['truck'] != ['car']`) |
| e9a9dee | A class added to the project after the session opened crashed Run (`KeyError`); now copied unchanged | 13 → 14 (`KeyError: 'late'`) |
| a9792d6 | Rewrite on widgets + bare hardened image (see below) | 14 → 22 |
| 15189fd | A failure during the copy left a half-filled `(merged classes)` project that looked complete. It is now removed (only the project this run created) and the error is shown | 22 → 23 (`[] != [1000]`) |

23/23 pass on macOS Python 3.14.3 and inside `supervisely/base-py-sdk-hardened:6.74.34` (Python 3.14.7, amd64).
`ruff check` / `ruff format --check` clean.

**Equivalence.** The old core (`ca304a1`, verbatim from v1.3.7) and the new core were run in memory on
real dev annotations (read only):
- #1317 merge-all into Apple: 22 images, 24 labels;
- #9390 building→roof and roof→building: 2 images, 17 labels.

Result: 0 differences and equal metas.

### Intentional changes

1. **Impossible merges are refused up front** (dffccaf). The dialog lists them and nothing is created.
   The per-class select no longer offers keypoint classes with different node labels.
2. **Failed runs leave no partial project** (15189fd). This is not the convert-class-shape v0.12.0
   behaviour, which keeps the partial project: pick one rule for both.
3. **Keypoint objects keep tags, description and binding** (9dfd767).
4. **Class-limited tags are retargeted** (8e65901).
5. **Classes added after the session opened** are copied unchanged instead of crashing.
6. **Widget UI** instead of `gui_template`:
   - same cards, texts, warning and result;
   - the class color is a dot, not a hex code;
   - the list is always sorted by name;
   - the "merge all" select preselects the first class (it used to be empty, and Run then crashed on an
     `assert`);
   - a failure no longer kills the session: the page unlocks and the error is shown.
7. **A project without images opens** (the old preview URL call got `None`).
8. README: added "merge all", nested datasets, the shape rules and the tag retargeting.

`config.json` `name`, `context_menu`, `modal_template`, the result name/description, `instance_version`
6.17.22 and SDK 6.74.34 are unchanged.

### Checked, no issue

- **In place?** No. The app always copies into a new project; the source project and meta are only read.
- **Nested datasets:** handled before (`dataset.tree`) and now (`get_list(recursive=True)` + parents first).
- **Empty datasets, images without annotations:** fine.
- **Security:** no archives, pickle, `eval`, shell or file paths from user data.
  - `debug.env` in history has only placeholders; it is removed.
  - `ecosystem-security.md` has no entry for this repo.

### Found, not fixed

- **Chained merges** (A→B and B→C) give B with A's objects plus C with B's. That is the old behaviour and
  it is not validated.
- **Image `custom_data`** is not copied (`upload_ids` passes `meta` only). Same as before, and same in
  convert-class-shape.
- **Keypoint classes whose objects reference node ids missing from their template** raise `KeyError`
  mid-copy. With the new cleanup, the partial project is removed.
- **Dropped CI job (open decision):** `release.yml` has no image build job, and none is needed. Nothing
  to drop here.

## Image

`supervisely/base-py-sdk:6.74.34` (shared `sdk_legacy`, Python 3.8) → `supervisely/base-py-sdk-hardened:6.74.34`.
- **Tag:** exists on Docker Hub (amd64, digest a9b9f147…).
- **Dependencies:** `dev_requirements.txt` = `supervisely==6.74.34` only. No per-app image and no build job.
- **SDK range:** 6.74.34 is inside the range `versions.json` allows for `instance_version` 6.17.22
  ([6.74.29, 6.74.35)).
- **Why not a fixes-only move:** AppService imports `agent_api`, which needs `protobuf<=3.20.3` (the
  `agent` extra). That is not in the hardened base, so the old code would have needed a per-app image
  pinned to old protobuf, plus the event-loop workaround that convert-class-shape once carried.

## Dev-check plan

The result goes to the **source project's workspace**, so run on copies in ws 733. #1317 lives in ws 3:
copy it to ws 733 first (`chk-mc-fruits`). #9390 is already in ws 733.

**Starting a session.** Each case starts with:
- branch: `uv run ecosystem-fleet/fleet.py run merge-classes --workspace 733 --project <id> --version ecosystem-fixes-2026-10 --branch --no-wait`;
- published: the same command without `--version/--branch` (v1.3.7).

Then drive Run over HTTP.

**Driving the branch session.** Read the widget ids from the page state:
- the class selects carry `value`;
- the "Merge all" checkbox carries `checked`;
- then POST `/<run button id>/button_clicked_cb` with that state.

**Driving the published session.** Send the `convert` command with `state.selectors` /
`state.mergeAll` / `state.mergeAllWith`. First send `mergeAllClassSelected`, because the old code reads
"merge all" from globals.

| # | Project / choice | Branch, expected | Published v1.3.7, expected |
|---|---|---|---|
| 1 | `chk-mc-fruits` (copy of 1317), Banana → Apple | `…(merged classes)`, 6 classes (no Banana), 22 images in the same nested tree, former Banana boxes are Apple | identical (except ids) |
| 2 | `chk-mc-fruits`, merge all into Apple | 1 class Apple, 24 labels, all images | identical |
| 3 | 9390, merge all into `blob` (bitmap) | error dialog listing 6 classes, **no project created**, session stays open | task crashes (`RuntimeError … Rectangle/Polygon != Bitmap`), a partial `ccs-synthetic-source(merged classes)` is left |
| 4 | 9390, building → roof | 6 classes (no building), 2 datasets incl. `child`, bound building objects keep their binding key on roof | identical |
| 5 | copy of 9390 with class `kp2` (graph, nodes `a`,`b`, other ids) and tag `seen` on the `kp` objects; kp → kp2 | kp objects become kp2, nodes match by label, **tag kept** | kp2 objects without the tag |
| 6 | copy of 9390 with tag `only_buildings` limited to `building`; building → roof | tag meta limited to `["roof"]` | still limited to `["building"]` |
| 7 | empty images project in ws 733 with two polygon classes | page opens; Run → empty project with 1 class, task output set | probably fails while opening (preview URL of `None`); record it |
| 8 | 9390, Run with nothing selected | warning "Please, define at least one transformation", nothing created | same |

Not verifiable on dev without fault injection: removing the partial project on a failure mid-copy
(15189fd). Covered by the offline test only.

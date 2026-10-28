"""Creates the copy of a project with the selected classes merged."""

from __future__ import annotations

from collections.abc import Callable, Mapping

import supervisely as sly

from src import platform_io
from src.core.datasets import parents_first
from src.core.merge import build_destination_meta, convert_annotation, destination_name, merge_problems

BATCH_SIZE = 50


class InvalidMerge(ValueError):
    """The selected merges cannot be done; raised before anything is created."""

    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("These classes cannot be merged, nothing was created:\n" + "\n".join(problems))


def merge_project(
    api: sly.Api,
    project: sly.ProjectInfo,
    selectors: Mapping[str, str],
    workspace_id: int | None = None,
    progress: Callable[[int], object] | None = None,
) -> sly.ProjectInfo:
    """Copy `project` into a new project `<name>(merged classes)` with the selected classes merged.

    `selectors` maps a class name to the class it is merged into (or "remain unchanged"). The mapping is
    checked against the current project meta first; `InvalidMerge` means nothing was created.
    The new project goes to `workspace_id` (default: the source project's workspace) and keeps the
    dataset tree, image names and image meta. The source project is only read. `progress` is called
    with the number of images done after every batch.
    """
    meta = platform_io.get_meta(api, project.id)
    problems = merge_problems(meta, selectors)
    if problems:
        raise InvalidMerge(problems)
    destination_meta = build_destination_meta(meta, selectors)

    target_workspace = project.workspace_id if workspace_id is None else workspace_id
    destination = platform_io.create_project(api, target_workspace, destination_name(project.name), destination_meta)
    sly.logger.info(f"Created project {destination.name!r} (id {destination.id})")

    try:
        new_dataset_ids: dict[int, int] = {}
        for dataset in parents_first(platform_io.list_datasets(api, project.id)):
            parent_id = new_dataset_ids.get(dataset.parent_id) if dataset.parent_id is not None else None
            new_dataset = platform_io.create_dataset(api, destination.id, dataset.name, parent_id)
            new_dataset_ids[dataset.id] = new_dataset.id

            images = platform_io.list_images(api, dataset.id)
            for batch in sly.batched(images, BATCH_SIZE):
                anns = platform_io.download_annotations(api, dataset.id, batch, meta)
                merged = [convert_annotation(ann, destination_meta, selectors) for ann in anns]
                platform_io.copy_images(api, new_dataset.id, batch, merged)
                if progress is not None:
                    progress(len(batch))
    except BaseException:
        # the project was created by this run and is incomplete: do not leave it looking like a result
        platform_io.remove_incomplete_project(api, destination)
        raise

    return platform_io.refresh_project(api, destination.id)

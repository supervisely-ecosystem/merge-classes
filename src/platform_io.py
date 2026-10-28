"""Every Supervisely API call the app makes."""

from __future__ import annotations

from collections.abc import Sequence

import supervisely as sly

DESCRIPTION = "(merged classes)"


def get_project(api: sly.Api, project_id: int) -> sly.ProjectInfo:
    project = api.project.get_info_by_id(project_id, raise_error=True)
    if project.type != str(sly.ProjectType.IMAGES):
        raise ValueError(f"Project {project.name!r} has type {project.type!r}; the app works only with images projects")
    return project


def get_meta(api: sly.Api, project_id: int) -> sly.ProjectMeta:
    return sly.ProjectMeta.from_json(api.project.get_meta(project_id))


def list_datasets(api: sly.Api, project_id: int) -> list[sly.DatasetInfo]:
    return api.dataset.get_list(project_id, recursive=True)


def create_project(api: sly.Api, workspace_id: int, name: str, meta: sly.ProjectMeta) -> sly.ProjectInfo:
    project = api.project.create(workspace_id, name, description=DESCRIPTION, change_name_if_conflict=True)
    api.project.update_meta(project.id, meta.to_json())
    return project


def create_dataset(api: sly.Api, project_id: int, name: str, parent_id: int | None) -> sly.DatasetInfo:
    return api.dataset.create(project_id, name, parent_id=parent_id)


def list_images(api: sly.Api, dataset_id: int) -> list[sly.ImageInfo]:
    return api.image.get_list(dataset_id)


def download_annotations(
    api: sly.Api, dataset_id: int, images: Sequence[sly.ImageInfo], meta: sly.ProjectMeta
) -> list[sly.Annotation]:
    infos = api.annotation.download_batch(dataset_id, [image.id for image in images])
    by_id = {info.image_id: info.annotation for info in infos}
    return [sly.Annotation.from_json(by_id[image.id], meta) for image in images]


def copy_images(api: sly.Api, dataset_id: int, images: Sequence[sly.ImageInfo], anns: Sequence[sly.Annotation]) -> None:
    """Add the images to the dataset by id (no re-upload of pixels) with their meta, then their annotations."""
    new_images = api.image.upload_ids(
        dataset_id,
        [image.name for image in images],
        [image.id for image in images],
        metas=[image.meta for image in images],
    )
    api.annotation.upload_anns([image.id for image in new_images], list(anns))


def remove_incomplete_project(api: sly.Api, project: sly.ProjectInfo) -> None:
    """Best effort: a failure here is logged, the original error is what the user must see."""
    try:
        api.project.remove(project.id)
        sly.logger.warning(f"Run failed: removed the incomplete project {project.name!r} (id {project.id})")
    except Exception:  # noqa: BLE001
        sly.logger.warning(
            f"Run failed and the incomplete project {project.name!r} (id {project.id}) could not be removed"
        )


def refresh_project(api: sly.Api, project_id: int) -> sly.ProjectInfo:
    """Project info after upload (the preview image is set only once the project has images)."""
    return api.project.get_info_by_id(project_id)


def set_task_output(api: sly.Api, project: sly.ProjectInfo) -> None:
    task_id = sly.env.task_id(raise_not_found=False)
    if task_id is not None:
        api.task.set_output_project(task_id, project.id, project.name)


def register_workflow_input(api: sly.Api, project_id: int) -> None:
    api.app.workflow.add_input_project(project_id)


def register_workflow_output(api: sly.Api, project_id: int) -> None:
    api.app.workflow.add_output_project(project_id)

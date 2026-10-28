"""merge_project end to end against an in-memory stand-in for the few API calls it makes."""

import itertools
from types import SimpleNamespace as NS

import pytest
import supervisely as sly

from src.core.merge import REMAIN_UNCHANGED, merge_all_selectors
from src.merger import InvalidMerge, merge_project

CAR = sly.ObjClass("car", sly.Polygon)
TRUCK = sly.ObjClass("truck", sly.Polygon)
SIGN = sly.ObjClass("sign", sly.Rectangle)
SEEN = sly.TagMeta("seen", sly.TagValueType.NONE)
META = sly.ProjectMeta(obj_classes=[CAR, TRUCK, SIGN], tag_metas=[SEEN])
TRI = sly.Polygon([sly.PointLocation(0, 0), sly.PointLocation(0, 5), sly.PointLocation(5, 5)])


def info(cls, **values):
    return cls(**{**{f: None for f in cls._fields}, **values})


class FakeApi:
    """Project 10 in workspace 5: root "train" (2 images) with nested "hard" (1 image), root "empty"."""

    def __init__(self, fail_upload_on_dataset: str | None = None):
        self._ids = itertools.count(1000)
        self.fail_upload_on_dataset = fail_upload_on_dataset
        self.source = info(sly.ProjectInfo, id=10, name="cars", workspace_id=5, type="images", items_count=3)
        self.datasets = [
            info(sly.DatasetInfo, id=2, name="hard", parent_id=1),  # listed before its parent on purpose
            info(sly.DatasetInfo, id=1, name="train", parent_id=None),
            info(sly.DatasetInfo, id=3, name="empty", parent_id=None),
        ]
        self.images = {
            1: [self._image(11, "a.jpg", {"k": 1}), self._image(12, "b.jpg", {})],
            2: [self._image(21, "c.jpg", {})],
            3: [],
        }
        mixed = sly.Annotation(
            (6, 8),
            labels=[
                sly.Label(TRI, TRUCK, tags=sly.TagCollection([sly.Tag(SEEN)]), binding_key="g"),
                sly.Label(sly.Rectangle(1, 1, 3, 4), SIGN, binding_key="g"),
            ],
        )
        self.anns = {11: mixed.to_json(), 12: sly.Annotation((6, 8)).to_json(), 21: mixed.to_json()}

        self.created_projects, self.created_datasets, self.uploaded_images, self.uploaded_anns = [], [], [], []
        self.metas = {10: META.to_json()}
        self.removed_projects = []
        self.project = NS(
            create=self._create_project,
            update_meta=self.metas.__setitem__,
            get_meta=self.metas.__getitem__,
            get_info_by_id=self._project,
            remove=self.removed_projects.append,
        )
        self.dataset = NS(get_list=self._list_datasets, create=self._create_dataset)
        self.image = NS(get_list=lambda ds_id: self.images[ds_id], upload_ids=self._upload_ids)
        self.annotation = NS(download_batch=self._download, upload_anns=self._upload_anns)

    @staticmethod
    def _image(image_id, name, image_meta):
        return info(sly.ImageInfo, id=image_id, name=name, meta=image_meta, width=8, height=6)

    def _create_project(self, workspace_id, name, description, change_name_if_conflict):
        assert change_name_if_conflict is True
        project = info(
            sly.ProjectInfo, id=next(self._ids), name=name, workspace_id=workspace_id, description=description
        )
        self.created_projects.append(project)
        return project

    def _project(self, project_id):
        return next(p for p in self.created_projects if p.id == project_id)

    def _list_datasets(self, project_id, recursive):
        assert (project_id, recursive) == (10, True)
        return self.datasets

    def _create_dataset(self, project_id, name, parent_id):
        dataset = info(sly.DatasetInfo, id=next(self._ids), name=name, parent_id=parent_id, project_id=project_id)
        self.created_datasets.append(dataset)
        return dataset

    def _download(self, dataset_id, image_ids):
        return [NS(image_id=i, annotation=self.anns[i]) for i in reversed(image_ids)]  # order is not guaranteed

    def _upload_ids(self, dataset_id, names, ids, metas):
        if any(d.id == dataset_id and d.name == self.fail_upload_on_dataset for d in self.created_datasets):
            raise ConnectionError("upload failed")
        new = [info(sly.ImageInfo, id=next(self._ids), name=n, dataset_id=dataset_id) for n in names]
        self.uploaded_images += [(dataset_id, n, i, m) for n, i, m in zip(names, ids, metas, strict=True)]
        return new

    def _upload_anns(self, image_ids, anns):
        self.uploaded_anns += list(zip(image_ids, anns, strict=True))


def selectors(**changes):
    return {c.name: changes.get(c.name, REMAIN_UNCHANGED) for c in META.obj_classes}


def test_copies_the_tree_and_merges_the_selected_classes():
    api = FakeApi()
    progress = []

    result = merge_project(api, api.source, selectors(truck="car"), progress=progress.append)

    assert (result.name, result.workspace_id, result.description) == ("cars(merged classes)", 5, "(merged classes)")
    meta = sly.ProjectMeta.from_json(api.metas[result.id])
    assert [c.name for c in meta.obj_classes] == ["car", "sign"]
    assert api.metas[10] == META.to_json()  # source meta untouched
    by_name = {d.name: d for d in api.created_datasets}
    assert set(by_name) == {"train", "hard", "empty"}
    assert by_name["hard"].parent_id == by_name["train"].id
    assert [(n, i, m) for _, n, i, m in api.uploaded_images] == [
        ("a.jpg", 11, {"k": 1}),
        ("b.jpg", 12, {}),
        ("c.jpg", 21, {}),
    ]
    first = api.uploaded_anns[0][1]
    assert [(lbl.obj_class.name, lbl.binding_key) for lbl in first.labels] == [("car", "g"), ("sign", "g")]
    assert [t.name for t in first.labels[0].tags] == ["seen"]
    assert sum(progress) == 3


def test_impossible_merge_creates_nothing():
    api = FakeApi()

    with pytest.raises(InvalidMerge) as error:
        merge_project(api, api.source, merge_all_selectors(META, "car"))

    assert error.value.problems == ["sign (rectangle) cannot be merged into car (polygon): shapes differ"]
    assert api.created_projects == [] and api.created_datasets == []


def test_output_workspace_can_be_redirected():
    api = FakeApi()

    result = merge_project(api, api.source, selectors(truck="car"), workspace_id=733)

    assert result.workspace_id == 733


def test_a_failure_halfway_removes_the_incomplete_result_project():
    api = FakeApi()
    api.fail_upload_on_dataset = "hard"  # copied after "train"

    with pytest.raises(ConnectionError):
        merge_project(api, api.source, selectors(truck="car"))

    assert len(api.uploaded_images) == 2  # "train" was already copied
    assert api.removed_projects == [api.created_projects[0].id]

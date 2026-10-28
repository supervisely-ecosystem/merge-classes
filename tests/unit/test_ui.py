"""The GUI in-process through Application.test_client: rendering and the Run handler."""

import asyncio

import pytest
import supervisely as sly
from supervisely.app import DataJson, StateJson
from supervisely.app.singleton import Singleton

from src.merger import InvalidMerge
from src.ui import MergeClassesGui

CAR = sly.ObjClass("car", sly.Polygon)
TRUCK = sly.ObjClass("truck", sly.Polygon)
SIGN = sly.ObjClass("sign", sly.Rectangle)
META = sly.ProjectMeta(obj_classes=[TRUCK, SIGN, CAR])


def info(cls, **values):
    return cls(**{**{f: None for f in cls._fields}, **values})


PROJECT = info(sly.ProjectInfo, id=10, name="cars", items_count=4, reference_image_url=None, type="images")
RESULT = info(sly.ProjectInfo, id=11, name="cars(merged classes)", items_count=4, reference_image_url=None)


@pytest.fixture(autouse=True)
def fresh_app(monkeypatch):
    monkeypatch.setenv("ENV", "development")
    Singleton._instances.clear()
    yield
    Singleton._instances.clear()


class Recorder:
    def __init__(self, error=None):
        self.calls, self.finished, self.error = [], [], error

    def merge(self, selectors, progress):
        self.calls.append(selectors)
        if self.error is not None:
            raise self.error
        for _ in range(4):
            progress(1)
        return RESULT


def make(recorder):
    gui = MergeClassesGui(PROJECT, META, recorder.merge, recorder.finished.append)
    return gui, sly.Application(layout=gui.layout)


def click(app, gui, values, merge_all=None):
    state = dict(StateJson())
    for name, value in values.items():
        state[gui.selectors[name].widget_id] = {**state[gui.selectors[name].widget_id], "value": value}
    if merge_all is not None:
        state[gui.merge_all.widget_id] = {**state[gui.merge_all.widget_id], "checked": True}
        state[gui.merge_all_with.widget_id] = {**state[gui.merge_all_with.widget_id], "value": merge_all}
    route = f"/{gui.run_button.widget_id}/button_clicked_cb"
    return asyncio.run(app.test_client.post(route, json={"state": state, "context": {}}))


def test_page_renders_one_selector_per_class_sorted_by_name():
    gui, app = make(Recorder())

    response = asyncio.run(app.test_client.get("/"))

    assert response.status_code == 200
    assert list(gui.selectors) == ["car", "sign", "truck"]
    assert [i.value for i in gui.selectors["car"].get_items()] == ["remain unchanged", "truck"]
    assert [i.value for i in gui.selectors["sign"].get_items()] == ["remain unchanged"]
    assert DataJson()[gui.selectors["sign"].widget_id]["disabled"] is True
    assert [i.value for i in gui.merge_all_with.get_items()] == ["car", "sign", "truck"]


def test_run_without_a_transformation_shows_a_warning():
    recorder = Recorder()
    gui, app = make(recorder)

    assert click(app, gui, {}).status_code == 200

    assert recorder.calls == []
    assert StateJson()["slyAppShowDialog"] is True
    assert DataJson()["slyAppDialogMessage"] == "Please, define at least one transformation"


def test_run_merges_the_selected_classes_and_shows_the_result():
    recorder = Recorder()
    gui, app = make(recorder)

    assert click(app, gui, {"truck": "car"}).status_code == 200

    assert recorder.calls == [{"car": "remain unchanged", "sign": "remain unchanged", "truck": "car"}]
    assert recorder.finished == [RESULT]
    assert DataJson()[gui.result.widget_id]["id"] == RESULT.id
    assert DataJson()[gui.run_button.widget_id]["disabled"] is True


def test_merge_all_sends_every_class_to_the_chosen_one():
    recorder = Recorder()
    gui, app = make(recorder)

    assert click(app, gui, {}, merge_all="truck").status_code == 200

    assert recorder.calls == [{"truck": "remain unchanged", "sign": "truck", "car": "truck"}]


def test_impossible_merge_shows_the_reasons_and_unlocks_the_page():
    recorder = Recorder(error=InvalidMerge(["sign (rectangle) cannot be merged into car (polygon): shapes differ"]))
    gui, app = make(recorder)

    assert click(app, gui, {}, merge_all="car").status_code == 200

    assert recorder.finished == []
    assert StateJson()["slyAppShowDialog"] is True
    assert "sign (rectangle) cannot be merged into car" in DataJson()["slyAppDialogMessage"]
    assert DataJson()[gui.run_button.widget_id]["disabled"] is False

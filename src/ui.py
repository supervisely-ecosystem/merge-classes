"""GUI: source project, "merge all" switch, one merge selector per class, Run button, result project."""

from __future__ import annotations

from collections.abc import Callable

import supervisely as sly
from supervisely.app.widgets import (
    Button,
    Card,
    Checkbox,
    Container,
    ObjectClassView,
    Progress,
    ProjectThumbnail,
    Select,
    Text,
)

from src.core.merge import REMAIN_UNCHANGED, has_changes, merge_all_selectors, merge_targets
from src.merger import InvalidMerge

# (selectors, progress callback) -> created project
MergeFn = Callable[[dict[str, str], Callable[[int], object]], sly.ProjectInfo]


class MergeClassesGui:
    """Widgets and the Run handler. Platform side effects come in through `merge` and `on_finished`."""

    def __init__(
        self,
        project: sly.ProjectInfo,
        meta: sly.ProjectMeta,
        merge: MergeFn,
        on_finished: Callable[[sly.ProjectInfo], None],
    ):
        self._project = project
        self._meta = meta
        self._merge = merge
        self._on_finished = on_finished

        classes = sorted(meta.obj_classes, key=lambda c: c.name)
        targets = merge_targets(meta)
        self.selectors: dict[str, Select] = {}
        rows = []
        for obj_class in classes:
            options = [REMAIN_UNCHANGED, *targets[obj_class.name]]
            select = Select(items=[Select.Item(value, value) for value in options], width_px=220)
            if len(options) == 1:
                select.disable()
            self.selectors[obj_class.name] = select
            rows.append(
                Container(
                    [ObjectClassView(obj_class, show_shape_icon=True), select],
                    direction="horizontal",
                    fractions=[1, 1],
                )
            )
        self.rows = (
            Container(rows) if rows else Text("The project has no classes, there is nothing to merge.", "warning")
        )

        self.merge_all = Checkbox("Merge all classes into one")
        self.merge_all_with = Select(
            items=[Select.Item(c.name, c.name) for c in classes],
            placeholder="Select a class to merge with",
            width_px=220,
        )
        self.merge_all_with.hide()
        self.merge_all.value_changed(self._merge_all_changed)

        self.run_button = Button("Run", icon="zmdi zmdi-play")
        self.progress = Progress(hide_on_finish=True)
        self.result_text = Text("New project has been successfully created", "success")
        self.result = ProjectThumbnail()
        self.result_text.hide()
        self.result.hide()

        input_card = Card("Input", content=ProjectThumbnail(_thumbnail_info(project)))
        output_card = Card(
            "Output",
            'Result project name = original name + "(merged classes)"; the original project is not changed',
            content=Container([self.run_button, self.progress, self.result_text, self.result]),
        )
        classes_card = Card(
            "Merge classes",
            "Define how to merge one or several classes",
            content=Container([self.merge_all, self.merge_all_with, self.rows]),
        )
        self.layout = Container(
            [Container([input_card, output_card], direction="horizontal", fractions=[1, 2]), classes_card]
        )
        self.run_button.click(self.run)

    def selected(self) -> dict[str, str]:
        """Class name -> class it is merged into (or "remain unchanged")."""
        if self.merge_all.is_checked():
            target = self.merge_all_with.get_value()
            return merge_all_selectors(self._meta, target) if target else {}
        return {name: select.get_value() for name, select in self.selectors.items()}

    def run(self) -> None:
        selectors = self.selected()
        if not has_changes(selectors):
            sly.app.show_dialog("Warning", "Please, define at least one transformation", status="warning")
            return

        self._set_locked(True)
        try:
            with self.progress(message="Merging classes", total=self._project.items_count or 0) as bar:
                destination = self._merge(selectors, bar.update)
        except InvalidMerge as error:
            self._set_locked(False)
            sly.app.show_dialog("Classes cannot be merged", str(error), status="error")
            return
        except Exception:
            self._set_locked(False)
            raise
        self.run_button.hide()
        self.result.set(_thumbnail_info(destination))
        self.result.show()
        self.result_text.show()
        self._on_finished(destination)

    def _merge_all_changed(self, checked: bool) -> None:
        if checked:
            self.merge_all_with.show()
            self.rows.hide()
        else:
            self.merge_all_with.hide()
            self.rows.show()

    def _set_locked(self, locked: bool) -> None:
        widgets = [
            self.run_button,
            self.merge_all,
            self.merge_all_with,
            *(s for s in self.selectors.values() if len(s.get_items()) > 1),
        ]
        for widget in widgets:
            if locked:
                widget.disable()
            else:
                widget.enable()


def _thumbnail_info(project: sly.ProjectInfo) -> sly.ProjectInfo:
    """ProjectThumbnail fails on a project without images (no preview url); show it without a preview."""
    if project.reference_image_url is None:
        return project._replace(reference_image_url="")
    return project

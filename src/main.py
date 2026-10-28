"""Merge classes: GUI app started from an images project's "Transform" menu.

Run with `uvicorn src.main:app` (see config.json `entrypoint`). This module is the composition root:
it reads the task context, creates the Api and wires the GUI to the merge and platform outputs.
"""

from __future__ import annotations

import os

import supervisely as sly
from dotenv import load_dotenv

from src import platform_io
from src.merger import merge_project
from src.settings import Settings
from src.ui import MergeClassesGui


def create_app() -> sly.Application:
    if not sly.is_production():
        load_dotenv("local.env")
        load_dotenv(os.path.expanduser("~/supervisely.env"))

    settings = Settings.from_env()
    api = sly.Api.from_env()
    project = platform_io.get_project(api, settings.project_id)
    meta = platform_io.get_meta(api, project.id)

    def merge(selectors: dict[str, str], progress) -> sly.ProjectInfo:
        platform_io.register_workflow_input(api, project.id)
        return merge_project(api, project, selectors, progress=progress)

    def finished(destination: sly.ProjectInfo) -> None:
        platform_io.set_task_output(api, destination)
        platform_io.register_workflow_output(api, destination.id)
        sly.logger.info("Destination project is created", extra={"project_id": destination.id})
        app.stop()  # the session closes itself; its page stays readable from the tasks list

    gui = MergeClassesGui(project, meta, merge, finished)
    app = sly.Application(layout=gui.layout)
    return app


app = create_app()

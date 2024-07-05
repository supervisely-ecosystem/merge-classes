import os

import supervisely as sly
from dotenv import load_dotenv

if sly.is_development():
    load_dotenv(os.path.expanduser("~/supervisely.env"))
    load_dotenv("local.env")

team_id = sly.env.team_id()
workspace_id = sly.env.workspace_id()
project_id = sly.env.project_id()
sly.logger.debug(
    f"Current context: team_id={team_id}, workspace_id={workspace_id}, project_id={project_id}"
)

api = sly.Api.from_env()
sly.logger.debug(f"API server address: {api.server_address}")
project_info = api.project.get_info_by_id(project_id)
project_meta = sly.ProjectMeta.from_json(api.project.get_meta(project_id))
sly.logger.debug(f"Project name: {project_info.name}, meta retrieved.")

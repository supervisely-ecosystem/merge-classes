from supervisely.app.widgets import Button, Card, Container, Flexbox, ProjectThumbnail

from src.globals import project_info

input_project_thumbnail = ProjectThumbnail(info=project_info)
input_card = Card(
    "1️⃣ Input project",
    "The project from which you want to copy and merge classes.",
    content=input_project_thumbnail,
)

run_button = Button("Run", icon="zmdi zmdi-play")
output_project_thumbnail = ProjectThumbnail()  # TODO: Set after creating a new project.
output_project_thumbnail.hide()
output_card = Card(
    "3️⃣ Output project",
    "The project where the merged classes will be saved.",
    content=Container(widgets=[run_button, output_project_thumbnail]),
)

flexbox = Flexbox([input_card, output_card])

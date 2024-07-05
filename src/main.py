import supervisely as sly
from supervisely.app.widgets import Container

from src.ui.input_output import flexbox
from src.ui.merge_classes import card

layout = Container(widgets=[flexbox, card])
app = sly.Application(layout=layout)

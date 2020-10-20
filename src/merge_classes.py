import os
import supervisely_lib as sly

my_app = sly.AppService()

TEAM_ID = int(os.environ['context.teamId'])
WORKSPACE_ID = int(os.environ['context.workspaceId'])
PROJECT_ID = int(os.environ['modal.state.slyProjectId'])

ORIGINAL_META = None
REMAIN_UNCHANGED = "remain unchanged"

_SUFFIX = "(merged classes)"

SHAPE_TO_ICON = {
    sly.Rectangle: {"icon": "zmdi zmdi-crop-din", "color": "#ea9d22", "bg": "#fcefd9"},
    sly.Bitmap: {"icon": "zmdi zmdi-brush", "color": "#ff8461", "bg": "#ffebe3"},
    sly.Polygon: {"icon": "icons8-polygon", "color": "#2cd26e", "bg": "#d8f8e7"},
    sly.AnyGeometry: {"icon": "zmdi zmdi-grain", "color": "#e09e11", "bg": "#faf0d8"},
    sly.Polyline: {"icon": "zmdi zmdi-minus", "color": "#ceadff", "bg": "#f6ebff"},
    sly.Point: {"icon": "zmdi zmdi-dot-circle-alt", "color": "#899aff", "bg": "#edeeff"},
}

UNKNOWN_ICON = {"icon": "zmdi zmdi-shape", "color": "#ea9d22", "bg": "#fcefd9"}


def init_data_and_state(api: sly.Api):
    global ORIGINAL_META

    data = {}
    state = {}
    state["selectors"] = {}
    table = []

    meta_json = api.project.get_meta(PROJECT_ID)
    ORIGINAL_META = sly.ProjectMeta.from_json(meta_json)

    for obj_class in ORIGINAL_META.obj_classes:
        row = {
            "name": obj_class.name,
            "color": sly.color.rgb2hex(obj_class.color),
            "shape": obj_class.geometry_type.geometry_name(),
            "shapeIcon": SHAPE_TO_ICON.get(obj_class.geometry_type, UNKNOWN_ICON)
        }

        possible_classes = [{"value": REMAIN_UNCHANGED, "label": REMAIN_UNCHANGED}]
        for dest_class in ORIGINAL_META.obj_classes:
            if obj_class.name == dest_class.name or obj_class.geometry_type != dest_class.geometry_type:
                continue
            else:
                possible_classes.append({"value": dest_class.name, "label": dest_class.name})

        sly.logger.debug("{!r} -> {}".format(obj_class.name, possible_classes))

        row["mergeWith"] = possible_classes
        state["selectors"][obj_class.name] = REMAIN_UNCHANGED
        table.append(row)

    data["table"] = table

    data["projectId"] = PROJECT_ID
    project = api.project.get_info_by_id(PROJECT_ID)
    data["projectName"] = project.name
    data["projectPreviewUrl"] = api.image.preview_url(project.reference_image_url, 100, 100)
    return data, state


def convert_annotation(ann: sly.Annotation, dst_meta, selectors):
    new_labels = []
    for lbl in ann.labels:
        dst_name = selectors[lbl.obj_class.name]
        if dst_name == REMAIN_UNCHANGED:
            new_labels.append(lbl)
        else:
            new_labels.append(lbl.clone(obj_class=dst_meta.get_obj_class(dst_name)))
    return ann.clone(labels=new_labels)


@my_app.callback("convert")
@sly.timeit
def convert(api: sly.Api, task_id, context, state, app_logger):
    api.task.set_field(task_id, "data.started", True)

    TEAM_ID = int(os.environ['context.teamId'])
    WORKSPACE_ID = int(os.environ['context.workspaceId'])
    PROJECT_ID = int(os.environ['modal.state.slyProjectId'])
    src_project = api.project.get_info_by_id(PROJECT_ID)

    if src_project.type != str(sly.ProjectType.IMAGES):
        raise RuntimeError("Project {!r} has type {!r}. App works only with type {!r}"
                           .format(src_project.name, src_project.type, sly.ProjectType.IMAGES))

    src_meta_json = api.project.get_meta(src_project.id)
    src_meta = sly.ProjectMeta.from_json(src_meta_json)

    dst_meta = src_meta.clone(obj_classes=sly.ObjClassCollection())
    need_action = False
    selectors = state["selectors"]
    for cls in src_meta.obj_classes:
        dst_name = selectors[cls.name]
        if dst_name == REMAIN_UNCHANGED:
            dst_cls = cls.clone()
        else:
            need_action = True
            dst_cls = src_meta.get_obj_class(dst_name).clone()
        if dst_meta.get_obj_class(dst_cls.name) is None:
            dst_meta = dst_meta.add_obj_class(dst_cls)

    if need_action is False:
        fields = [
            {
                "field": "state.showWarningDialog",
                "payload": True
            },
            {
                "field": "data.started",
                "payload": False,
            }
        ]
        api.task.set_fields(task_id, fields)
        return

    dst_name = src_project.name if _SUFFIX in src_project.name else src_project.name + _SUFFIX
    dst_project = api.project.create(src_project.workspace_id, dst_name, description=_SUFFIX, change_name_if_conflict=True)
    sly.logger.info('Destination project is created.',
                    extra={'project_id': dst_project.id, 'project_name': dst_project.name})
    api.project.update_meta(dst_project.id, dst_meta.to_json())

    total_progress = api.project.get_images_count(src_project.id)
    current_progress = 0
    ds_progress = sly.Progress('Processing:', total_cnt=total_progress)
    for ds_info in api.dataset.get_list(src_project.id):
        dst_dataset = api.dataset.create(dst_project.id, ds_info.name)
        img_infos_all = api.image.get_list(ds_info.id)

        for img_infos in sly.batched(img_infos_all):
            img_names, img_ids, img_metas = zip(*((x.name, x.id, x.meta) for x in img_infos))

            ann_infos = api.annotation.download_batch(ds_info.id, img_ids)
            anns = [sly.Annotation.from_json(x.annotation, src_meta) for x in ann_infos]

            new_anns = [convert_annotation(ann, dst_meta, selectors) for ann in anns]

            new_img_infos = api.image.upload_ids(dst_dataset.id, img_names, img_ids, metas=img_metas)
            new_img_ids = [x.id for x in new_img_infos]
            api.annotation.upload_anns(new_img_ids, new_anns)

            current_progress += len(img_infos)
            api.task.set_field(task_id, "data.progress", int(current_progress * 100 / total_progress))
            ds_progress.iters_done_report(len(img_infos))

    api.task.set_output_project(task_id, dst_project.id, dst_project.name)

    # to get correct "reference_image_url"
    res_project = api.project.get_info_by_id(dst_project.id)
    fields = [
        {
            "field": "data.resultProject",
            "payload": dst_project.name,
        },
        {
            "field": "data.resultProjectId",
            "payload": dst_project.id,
        },
        {
            "field": "data.resultProjectPreviewUrl",
            "payload": api.image.preview_url(res_project.reference_image_url, 100, 100),
        }
    ]
    api.task.set_fields(task_id, fields)
    my_app.stop()


def main():
    api = sly.Api.from_env()
    data, state = init_data_and_state(api)

    data["started"] = False
    data["progress"] = 0
    data["resultProject"] = ""

    state["showWarningDialog"] = False
    #state["showFinishDialog"] = False

    # Run application service
    my_app.run(data=data, state=state)


if __name__ == "__main__":
    sly.main_wrapper("main", main)
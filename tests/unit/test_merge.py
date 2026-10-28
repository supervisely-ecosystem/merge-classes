"""Pure merge logic on tiny in-memory SDK objects."""

import supervisely as sly
from supervisely.geometry.graph import KeypointsTemplate

from src.core.merge import (
    REMAIN_UNCHANGED,
    build_destination_meta,
    convert_annotation,
    destination_name,
    has_changes,
    merge_all_selectors,
    merge_problems,
    merge_targets,
)

CAR = sly.ObjClass("car", sly.Polygon, color=[255, 0, 0])
TRUCK = sly.ObjClass("truck", sly.Polygon, color=[0, 255, 0])
BOX = sly.ObjClass("box", sly.Rectangle, color=[0, 0, 255])
FREE = sly.ObjClass("free", sly.AnyGeometry)
SEEN = sly.TagMeta("seen", sly.TagValueType.NONE)
META = sly.ProjectMeta(obj_classes=[CAR, TRUCK, BOX, FREE], tag_metas=[SEEN])

SQUARE = sly.Polygon([sly.PointLocation(0, 0), sly.PointLocation(0, 5), sly.PointLocation(5, 5)])


def unchanged(meta=META, **changes):
    return {c.name: changes.get(c.name, REMAIN_UNCHANGED) for c in meta.obj_classes}


def keypoints_class(name, labels, color=(1, 2, 3)):
    template = KeypointsTemplate()
    for i, label in enumerate(labels):
        template.add_point(label=label, row=i, col=i)
    return sly.ObjClass(name, sly.GraphNodes, geometry_config=template, color=list(color))


def test_destination_name_adds_the_suffix_once():
    assert destination_name("fruits") == "fruits(merged classes)"
    assert destination_name("fruits(merged classes)") == "fruits(merged classes)"


def test_merge_targets_offer_other_classes_of_the_same_shape():
    assert merge_targets(META) == {"car": ["truck"], "truck": ["car"], "box": [], "free": []}


def test_merge_all_sends_every_class_to_the_target():
    assert merge_all_selectors(META, "car") == {
        "car": REMAIN_UNCHANGED,
        "truck": "car",
        "box": "car",
        "free": "car",
    }


def test_has_changes():
    assert has_changes(unchanged()) is False
    assert has_changes(unchanged(truck="car")) is True


def test_destination_meta_drops_merged_classes_and_keeps_the_rest():
    dst = build_destination_meta(META, unchanged(truck="car"))

    assert [c.name for c in dst.obj_classes] == ["car", "box", "free"]
    assert dst.get_obj_class("car") == CAR
    assert dst.tag_metas.get("seen") == SEEN


def test_labels_of_merged_classes_move_to_the_destination_class_with_their_tags():
    dst = build_destination_meta(META, unchanged(truck="car"))
    tag = sly.Tag(SEEN)
    label = sly.Label(SQUARE, TRUCK, tags=sly.TagCollection([tag]), description="d", binding_key="g1")
    other = sly.Label(sly.Rectangle(0, 0, 2, 2), BOX)
    ann = sly.Annotation((10, 10), labels=[label, other], img_tags=sly.TagCollection([tag]))

    new = convert_annotation(ann, dst, unchanged(truck="car"))

    assert [lbl.obj_class.name for lbl in new.labels] == ["car", "box"]
    moved = new.labels[0]
    assert moved.geometry == SQUARE
    assert [t.name for t in moved.tags] == ["seen"]
    assert (moved.description, moved.binding_key) == ("d", "g1")
    assert [t.name for t in new.img_tags] == ["seen"]


def test_keypoints_are_remapped_by_node_label():
    src = keypoints_class("pose_a", ["nose", "tail"])
    dst_class = keypoints_class("pose_b", ["tail", "nose"])
    meta = sly.ProjectMeta(obj_classes=[src, dst_class])
    selectors = unchanged(meta, pose_a="pose_b")
    dst_meta = build_destination_meta(meta, selectors)
    src_ids = {n["label"]: i for i, n in src.geometry_config["nodes"].items()}
    dst_ids = {n["label"]: i for i, n in dst_class.geometry_config["nodes"].items()}
    nodes = {
        src_ids["nose"]: sly.Node(sly.PointLocation(1, 1)),
        src_ids["tail"]: sly.Node(sly.PointLocation(7, 7)),
    }
    ann = sly.Annotation((10, 10), labels=[sly.Label(sly.GraphNodes(nodes), src)])

    new = convert_annotation(ann, dst_meta, selectors)

    label = new.labels[0]
    assert label.obj_class.name == "pose_b"
    assert _rc(label.geometry.nodes[dst_ids["nose"]]) == (1, 1)
    assert _rc(label.geometry.nodes[dst_ids["tail"]]) == (7, 7)


def _rc(node):
    return node.location.row, node.location.col


def test_merged_keypoints_keep_tags_description_and_binding():
    src = keypoints_class("pose_a", ["nose", "tail"])
    dst_class = keypoints_class("pose_b", ["nose", "tail"])
    meta = sly.ProjectMeta(obj_classes=[src, dst_class], tag_metas=[SEEN])
    selectors = unchanged(meta, pose_a="pose_b")
    dst_meta = build_destination_meta(meta, selectors)
    nodes = {i: sly.Node(sly.PointLocation(1, 1)) for i in src.geometry_config["nodes"]}
    label = sly.Label(
        sly.GraphNodes(nodes), src, tags=sly.TagCollection([sly.Tag(SEEN)]), description="d", binding_key="g1"
    )

    new = convert_annotation(sly.Annotation((10, 10), labels=[label]), dst_meta, selectors).labels[0]

    assert [t.name for t in new.tags] == ["seen"]
    assert (new.description, new.binding_key) == ("d", "g1")


def test_merge_all_into_a_class_of_another_shape_is_refused_before_anything_is_created():
    problems = merge_problems(META, merge_all_selectors(META, "car"))

    assert problems == [
        "box (rectangle) cannot be merged into car (polygon): shapes differ",
        "free (any) cannot be merged into car (polygon): shapes differ",
    ]


def test_merge_all_into_an_any_shape_class_is_allowed_except_keypoints():
    pose = keypoints_class("pose", ["nose"])
    meta = META.add_obj_class(pose)

    problems = merge_problems(meta, merge_all_selectors(meta, "free"))

    assert problems == ["pose (graph) cannot be merged into free (any): shapes differ"]


def test_keypoints_with_different_templates_are_not_offered_and_are_refused():
    a = keypoints_class("pose_a", ["nose", "tail"])
    b = keypoints_class("pose_b", ["nose", "ear"])
    c = keypoints_class("pose_c", ["tail", "nose"])
    meta = sly.ProjectMeta(obj_classes=[a, b, c])

    assert merge_targets(meta) == {"pose_a": ["pose_c"], "pose_b": [], "pose_c": ["pose_a"]}
    assert merge_problems(meta, unchanged(meta, pose_a="pose_b")) == [
        "pose_a (graph) cannot be merged into pose_b (graph): keypoint templates differ"
    ]
    assert merge_problems(meta, unchanged(meta, pose_a="pose_c")) == []


def test_merge_all_into_an_any_shape_class_converts_every_shape():
    selectors = merge_all_selectors(META, "free")
    assert merge_problems(META, selectors) == []
    dst = build_destination_meta(META, selectors)
    labels = [sly.Label(SQUARE, CAR), sly.Label(sly.Rectangle(0, 0, 2, 2), BOX), sly.Label(sly.Point(1, 1), FREE)]

    new = convert_annotation(sly.Annotation((10, 10), labels=labels), dst, selectors)

    assert [c.name for c in dst.obj_classes] == ["free"]
    assert [(lbl.obj_class.name, type(lbl.geometry)) for lbl in new.labels] == [
        ("free", sly.Polygon),
        ("free", sly.Rectangle),
        ("free", sly.Point),
    ]


def test_tags_limited_to_a_merged_class_now_apply_to_its_destination():
    only_trucks = sly.TagMeta("axles", sly.TagValueType.ANY_NUMBER, applicable_classes=["truck"])
    both = sly.TagMeta("damaged", sly.TagValueType.NONE, applicable_classes=["truck", "car"])
    meta = META.add_tag_metas([only_trucks, both])

    dst = build_destination_meta(meta, unchanged(meta, truck="car"))

    assert dst.get_tag_meta("axles").applicable_classes == ["car"]
    assert dst.get_tag_meta("damaged").applicable_classes == ["car"]
    assert dst.get_tag_meta("seen").applicable_classes == []

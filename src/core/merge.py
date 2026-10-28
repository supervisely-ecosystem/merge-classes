"""Pure merge logic: which classes can merge, the destination meta and annotation conversion.

No Api, no env, no GUI: everything here works on SDK data classes and is unit-tested.
"""

from __future__ import annotations

from collections.abc import Mapping

import supervisely as sly

REMAIN_UNCHANGED = "remain unchanged"
SUFFIX = "(merged classes)"


def destination_name(source_name: str) -> str:
    """`<name>(merged classes)`; a name that already has the suffix is kept (the platform adds `_001`...)."""
    return source_name if SUFFIX in source_name else source_name + SUFFIX


def merge_targets(meta: sly.ProjectMeta) -> dict[str, list[str]]:
    """For every class, the classes it can be merged into (the per-class dropdown, without "remain unchanged").

    Only classes of the same shape are offered; keypoint classes only when their templates match.
    """
    targets = {}
    for obj_class in meta.obj_classes:
        targets[obj_class.name] = [
            dst.name
            for dst in meta.obj_classes
            if dst.name != obj_class.name
            and dst.geometry_type == obj_class.geometry_type
            and _merge_problem(obj_class, dst) is None
        ]
    return targets


def merge_problems(meta: sly.ProjectMeta, selectors: Mapping[str, str]) -> list[str]:
    """Why the selected merges cannot be done; empty when every merge is valid.

    Checked before anything is created, so an invalid mapping never leaves a half-filled project.
    A class can be merged into a class of the same shape (keypoints: same node labels) or into an
    `any` shape class (not keypoints: their nodes need a template).
    """
    problems = []
    for src in meta.obj_classes:
        dst_name = selectors.get(src.name, REMAIN_UNCHANGED)
        if dst_name == REMAIN_UNCHANGED:
            continue
        dst = meta.get_obj_class(dst_name)
        if dst is None:
            problems.append(f"{src.name}: destination class {dst_name!r} is not in the project")
            continue
        problem = _merge_problem(src, dst)
        if problem is not None:
            problems.append(f"{src.name} ({_shape(src)}) cannot be merged into {dst.name} ({_shape(dst)}): {problem}")
    return problems


def _shape(obj_class: sly.ObjClass) -> str:
    return obj_class.geometry_type.geometry_name()


def _node_labels(obj_class: sly.ObjClass) -> list[str]:
    return sorted(node["label"] for node in obj_class.geometry_config.get("nodes", {}).values())


def _merge_problem(src: sly.ObjClass, dst: sly.ObjClass) -> str | None:
    if dst.geometry_type is sly.AnyGeometry and src.geometry_type is not sly.GraphNodes:
        return None
    if src.geometry_type != dst.geometry_type:
        return "shapes differ"
    if src.geometry_type is sly.GraphNodes:
        labels = _node_labels(src)
        if not labels or labels != _node_labels(dst) or len(set(labels)) != len(labels):
            return "keypoint templates differ"
    return None


def merge_all_selectors(meta: sly.ProjectMeta, target: str) -> dict[str, str]:
    """ "Merge all classes into one": every class goes to `target`, the target itself stays."""
    return {c.name: REMAIN_UNCHANGED if c.name == target else target for c in meta.obj_classes}


def has_changes(selectors: Mapping[str, str]) -> bool:
    return any(value != REMAIN_UNCHANGED for value in selectors.values())


def build_destination_meta(src_meta: sly.ProjectMeta, selectors: Mapping[str, str]) -> sly.ProjectMeta:
    """Source meta without the merged-away classes; tags and settings are kept."""
    dst_meta = src_meta.clone(obj_classes=sly.ObjClassCollection())
    for cls in src_meta.obj_classes:
        dst_name = selectors.get(cls.name, REMAIN_UNCHANGED)
        if dst_name == REMAIN_UNCHANGED:
            dst_cls = cls.clone()
        else:
            dst_cls = src_meta.get_obj_class(dst_name).clone()
        if dst_meta.get_obj_class(dst_cls.name) is None:
            dst_meta = dst_meta.add_obj_class(dst_cls)
    return _retarget_tag_metas(dst_meta, selectors)


def _retarget_tag_metas(meta: sly.ProjectMeta, selectors: Mapping[str, str]) -> sly.ProjectMeta:
    """Tags limited to a merged-away class become applicable to its destination class instead."""
    tag_metas = []
    for tag_meta in meta.tag_metas:
        names = tag_meta.applicable_classes
        if names:
            renamed = [selectors.get(n, REMAIN_UNCHANGED) for n in names]
            renamed = [new if new != REMAIN_UNCHANGED else old for old, new in zip(names, renamed, strict=True)]
            tag_meta = tag_meta.clone(applicable_classes=list(dict.fromkeys(renamed)))
        tag_metas.append(tag_meta)
    return meta.clone(tag_metas=sly.TagMetaCollection(tag_metas))


def convert_annotation(ann: sly.Annotation, dst_meta: sly.ProjectMeta, selectors: Mapping[str, str]) -> sly.Annotation:
    """Reassign the labels of merged classes to their destination class; other labels are kept."""
    new_labels = []
    for lbl in ann.labels:
        dst_name = selectors.get(lbl.obj_class.name, REMAIN_UNCHANGED)
        if dst_name == REMAIN_UNCHANGED:
            new_labels.append(lbl)
        elif isinstance(lbl.geometry, sly.GraphNodes):
            dst_obj_class = dst_meta.get_obj_class(dst_name)
            new_labels.append(_remap_keypoints(lbl, dst_obj_class))
        else:
            new_labels.append(lbl.clone(obj_class=dst_meta.get_obj_class(dst_name)))
    return ann.clone(labels=new_labels)


def _remap_keypoints(lbl: sly.Label, dst_obj_class: sly.ObjClass) -> sly.Label:
    """Keypoints: node ids differ between templates, so nodes are matched by their label."""
    orig_obj_class = lbl.obj_class
    dst_geom_nodes = dst_obj_class.geometry_config.get("nodes", {})
    orig_geom_nodes = orig_obj_class.geometry_config.get("nodes", {})
    if not dst_geom_nodes or not orig_geom_nodes:
        sly.logger.warning("One of the geometry configs does not have nodes")
    if len(dst_geom_nodes) != len(orig_geom_nodes):
        raise ValueError(
            "Graph templates contain different number of templates, "
            "but only keypoint classes with the same number of nodes can be merged"
        )
    dst_node_labels = [value["label"] for value in dst_geom_nodes.values()]
    orig_node_labels = [value["label"] for value in orig_geom_nodes.values()]
    if set(dst_node_labels) != set(orig_node_labels):
        raise ValueError(
            "Graph templates have different node labels, "
            "but only keypoint classes with the same node labels can be merged"
        )
    orig_node_id2label = {node_id: node["label"] for node_id, node in orig_geom_nodes.items()}
    dst_label2_node_id = {node["label"]: node_id for node_id, node in dst_geom_nodes.items()}
    new_nodes = {}
    for node_id, node in lbl.geometry.nodes.items():
        new_nodes[dst_label2_node_id[orig_node_id2label[node_id]]] = node
    # clone keeps the object's tags, description and binding key
    return lbl.clone(geometry=sly.GraphNodes(new_nodes), obj_class=dst_obj_class)

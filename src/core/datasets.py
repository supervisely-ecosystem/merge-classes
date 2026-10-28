"""Dataset tree helpers on DatasetInfo-like objects (`id`, `parent_id`)."""

from __future__ import annotations

from collections.abc import Sequence


def parents_first[D](datasets: Sequence[D]) -> list[D]:
    """Order datasets so that every parent comes before its children; siblings keep their order."""
    by_id = {ds.id: ds for ds in datasets}

    def depth(ds) -> int:
        level = 0
        while ds.parent_id is not None and ds.parent_id in by_id:
            ds = by_id[ds.parent_id]
            level += 1
        return level

    return sorted(datasets, key=depth)

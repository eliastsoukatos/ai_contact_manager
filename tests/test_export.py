import sys
import types

sys.modules.setdefault("requests", types.SimpleNamespace(Session=lambda: None))

import exporter


def test_chunk_list_by_size():
    items = [{'id': i} for i in range(25)]
    chunks = exporter._chunk_list(items, groups=1, chunk_size=10)
    assert len(chunks) == 3
    assert [len(c) for c in chunks] == [10, 10, 5]


def test_chunk_list_groups_fallback():
    items = [{'id': i} for i in range(5)]
    chunks = exporter._chunk_list(items, groups=2)
    assert len(chunks) == 2
    assert sum(len(c) for c in chunks) == 5

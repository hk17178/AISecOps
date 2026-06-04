"""L02 Memory Store 测试。"""

from aisecops.L02_agents import InMemoryMemoryStore


def test_put_get() -> None:
    m = InMemoryMemoryStore()
    m.put("ns", "k", {"a": 1})
    assert m.get("ns", "k") == {"a": 1}
    assert m.get("ns", "missing") is None


def test_list_is_namespace_scoped() -> None:
    m = InMemoryMemoryStore()
    m.put("ns1", "a", {"v": 1})
    m.put("ns1", "b", {"v": 2})
    m.put("ns2", "c", {"v": 3})
    assert len(m.list("ns1")) == 2
    assert len(m.list("ns2")) == 1


def test_put_copies_value() -> None:
    """存入后外部修改原 dict 不应影响已存值。"""
    m = InMemoryMemoryStore()
    src = {"v": 1}
    m.put("ns", "k", src)
    src["v"] = 999
    assert m.get("ns", "k") == {"v": 1}

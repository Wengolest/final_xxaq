from pyrit.memory import MemoryInterface


def test_memory(sqlite_instance: MemoryInterface):
    assert sqlite_instance

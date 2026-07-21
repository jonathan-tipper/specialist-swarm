import json

from swarm.store import IdStore


def test_get_returns_none_when_absent(tmp_path):
    assert IdStore(tmp_path / ".swarm_ids.json").get("environment") is None


def test_set_then_get_roundtrips(tmp_path):
    store = IdStore(tmp_path / ".swarm_ids.json")
    store.set("environment", "env_abc")
    assert store.get("environment") == "env_abc"


def test_set_persists_to_disk(tmp_path):
    path = tmp_path / ".swarm_ids.json"
    IdStore(path).set("coordinator", "agent_xyz")
    assert json.loads(path.read_text()) == {"coordinator": "agent_xyz"}


def test_reload_from_disk(tmp_path):
    path = tmp_path / ".swarm_ids.json"
    IdStore(path).set("coordinator", "agent_xyz")
    assert IdStore(path).get("coordinator") == "agent_xyz"


def test_get_or_create_calls_factory_once(tmp_path):
    store = IdStore(tmp_path / ".swarm_ids.json")
    calls = []

    def factory():
        calls.append(1)
        return "agent_new"

    first, created_first = store.get_or_create("sre", factory)
    second, created_second = store.get_or_create("sre", factory)

    assert first == second == "agent_new"
    assert created_first is True
    assert created_second is False
    assert len(calls) == 1


def test_nested_namespace(tmp_path):
    store = IdStore(tmp_path / ".swarm_ids.json")
    store.set("specialists.sre", "agent_s")
    store.set("specialists.security", "agent_x")
    assert store.get("specialists.sre") == "agent_s"
    assert store.get("specialists") == {"sre": "agent_s", "security": "agent_x"}


def test_corrupt_file_raises_with_path_in_message(tmp_path):
    path = tmp_path / ".swarm_ids.json"
    path.write_text("{not json")
    try:
        IdStore(path).get("anything")
    except ValueError as exc:
        assert ".swarm_ids.json" in str(exc)
    else:
        raise AssertionError("expected ValueError")

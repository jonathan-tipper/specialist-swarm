from evals.fanout import is_parallel_fanout


def created(agent_name):
    return {"type": "session.thread_created", "agent_name": agent_name}


def received(agent_name):
    return {"type": "agent.thread_message_received", "from_agent_name": agent_name}


def test_three_threads_before_first_reply_is_parallel():
    events = [created("SRE"), created("Security"), created("Comms"), received("SRE")]
    assert is_parallel_fanout(events) is True


def test_reply_before_all_threads_created_is_serial():
    events = [created("SRE"), received("SRE"), created("Security"), created("Comms")]
    assert is_parallel_fanout(events) is False


def test_no_reply_at_all_is_not_parallel():
    events = [created("SRE"), created("Security"), created("Comms")]
    assert is_parallel_fanout(events) is False


def test_no_events_is_not_parallel():
    assert is_parallel_fanout([]) is False


def test_expected_agents_is_configurable():
    events = [created("A"), created("B"), received("A")]
    assert is_parallel_fanout(events, expected_agents=2) is True
    assert is_parallel_fanout(events, expected_agents=3) is False


def test_unrelated_events_are_ignored():
    events = [
        {"type": "agent.tool_use", "name": "bash"},
        created("SRE"),
        created("Security"),
        created("Comms"),
        {"type": "agent.tool_use", "name": "docx"},
        received("SRE"),
    ]
    assert is_parallel_fanout(events) is True

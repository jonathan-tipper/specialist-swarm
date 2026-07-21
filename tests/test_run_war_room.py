from run_war_room import kickoff_message


def test_kickoff_message_includes_incident_id():
    text = kickoff_message()
    assert "INC-4417" in text


def test_kickoff_message_includes_supporting_docs():
    text = kickoff_message()
    assert "service-topology.md" in text
    assert "recent-changes.json" in text
    assert "past-incidents.json" in text

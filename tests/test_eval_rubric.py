from evals.rubric import CRITERIA, build_judge_prompt


def test_prompt_includes_every_criterion_key():
    prompt = build_judge_prompt("postmortem body", "incident ticket body")
    for criterion in CRITERIA:
        assert criterion["key"] in prompt


def test_prompt_includes_source_texts():
    prompt = build_judge_prompt("UNIQUE POSTMORTEM TEXT", "UNIQUE TICKET TEXT")
    assert "UNIQUE POSTMORTEM TEXT" in prompt
    assert "UNIQUE TICKET TEXT" in prompt


def test_prompt_specifies_json_output_and_verdict_values():
    prompt = build_judge_prompt("body", "ticket")
    assert "JSON" in prompt
    assert "PASS" in prompt and "FAIL" in prompt and "PARTIAL" in prompt


def test_criteria_have_unique_keys():
    keys = [criterion["key"] for criterion in CRITERIA]
    assert len(keys) == len(set(keys))

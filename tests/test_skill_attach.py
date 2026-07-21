from anthropic.types.beta.beta_managed_agents_custom_skill import (
    BetaManagedAgentsCustomSkill,
)

from upload_skills import already_attached


def test_detects_an_attached_custom_skill():
    skills = [BetaManagedAgentsCustomSkill(type="custom", skill_id="skill_abc", version="latest")]
    assert already_attached(skills, "skill_abc") is True


def test_ignores_an_unrelated_skill():
    skills = [BetaManagedAgentsCustomSkill(type="custom", skill_id="skill_abc", version="latest")]
    assert already_attached(skills, "skill_xyz") is False


def test_empty_skill_list_is_not_attached():
    assert already_attached([], "skill_abc") is False

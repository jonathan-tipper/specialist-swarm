from evals.scorecard import Scorecard, render


def test_no_findings_passes():
    assert Scorecard().passed is True


def test_missing_sections_fails():
    card = Scorecard(missing_sections=["Timeline"])
    assert card.passed is False


def test_serial_fanout_fails():
    card = Scorecard(parallel_fanout=False)
    assert card.passed is False


def test_unset_fanout_does_not_fail():
    card = Scorecard(parallel_fanout=None)
    assert card.passed is True


def test_judged_failure_fails_overall():
    card = Scorecard(judged={"reconciliation": {"verdict": "FAIL", "evidence": "only names the deploy"}})
    assert card.passed is False


def test_judged_all_pass_passes_overall():
    card = Scorecard(judged={"blameless": {"verdict": "PASS", "evidence": "roles only"}})
    assert card.passed is True


def test_render_reports_overall_pass():
    assert "OVERALL: PASS" in render(Scorecard())


def test_render_reports_overall_fail():
    assert "OVERALL: FAIL" in render(Scorecard(missing_sections=["Timeline"]))


def test_render_shows_skip_when_fanout_not_checked():
    assert "SKIP" in render(Scorecard())

from swarm.runner import resolve_console_url


def test_uses_workspace_scoped_url_when_workspace_is_set():
    url = resolve_console_url("sesn_123", "wrkspc_abc")
    assert url == "https://platform.claude.com/workspaces/wrkspc_abc/sessions/sesn_123"


def test_falls_back_to_workspace_less_url_when_unset():
    """The literal string "default" is not a real workspace ID and 404s."""
    url = resolve_console_url("sesn_123", None)
    assert url == "https://platform.claude.com/sessions/sesn_123"
    assert "default" not in url

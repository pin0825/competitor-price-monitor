def test_dashboard_is_served(client) -> None:
    """루트 경로에서 포트폴리오 대시보드 HTML을 제공한다."""
    response = client.get("/")

    assert response.status_code == 200
    assert "PRISMA" in response.text
    assert "Competitor overview" in response.text
    assert 'src="/static/app.js"' in response.text


def test_dashboard_static_assets_are_served(client) -> None:
    """FastAPI가 대시보드의 CSS와 JavaScript 파일을 제공한다."""
    stylesheet = client.get("/static/styles.css")
    script = client.get("/static/app.js")

    assert stylesheet.status_code == 200
    assert "--mint:" in stylesheet.text
    assert script.status_code == 200
    assert 'const API_BASE = "/api/v1"' in script.text

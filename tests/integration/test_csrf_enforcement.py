from __future__ import annotations


def test_csrf_rejects_missing_token(client) -> None:
    client.get('/auth/login')
    response = client.post('/auth/login', data={'pin': '1224'})
    assert response.status_code == 403


def test_csrf_rejects_mismatched_token(client) -> None:
    client.get('/auth/login')
    response = client.post(
        '/auth/login',
        data={'pin': '1224'},
        headers={'x-csrf-token': 'mismatched-token'},
    )
    assert response.status_code == 403

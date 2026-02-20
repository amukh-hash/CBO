from app.services.sync.dedupe import dedupe_keys, make_idempotency_key


def test_dedupe_idempotency_keys() -> None:
    k1 = make_idempotency_key("2025-01-01", "100", "medical")
    k2 = make_idempotency_key("2025-01-01", "100", "medical")
    k3 = make_idempotency_key("2025-01-02", "100", "medical")
    assert k1 == k2
    assert k1 != k3
    assert dedupe_keys([k1, k2, k3]) == [k1, k3]

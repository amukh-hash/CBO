from app.core.crypto import FieldEncryptor


def test_field_encryption_roundtrip() -> None:
    enc = FieldEncryptor()
    value = "policy-12345"
    ciphertext = enc.encrypt(value)
    assert ciphertext != value
    assert enc.decrypt(ciphertext) == value

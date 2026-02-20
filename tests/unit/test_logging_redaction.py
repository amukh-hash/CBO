import logging

from app.core.logging import PHIRedactionFilter


def test_phi_strings_redacted_in_logs() -> None:
    record = logging.LogRecord(
        name="cb",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="John Doe ssn 123-45-6789 email jane@doe.com",
        args=(),
        exc_info=None,
    )
    filt = PHIRedactionFilter()
    assert filt.filter(record)
    assert "John Doe" not in record.msg
    assert "123-45-6789" not in record.msg
    assert "jane@doe.com" not in record.msg


def test_exc_info_removed_from_default_logs() -> None:
    record = logging.LogRecord(
        name="cb",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="failure",
        args=(),
        exc_info=(ValueError, ValueError("bad"), None),
    )
    filt = PHIRedactionFilter()
    assert filt.filter(record)
    assert record.exc_info is None

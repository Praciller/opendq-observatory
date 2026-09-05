from opendq.errors import ErrorCode, IngestionError


def test_error_code_is_public_and_stable() -> None:
    error = IngestionError(ErrorCode.SOURCE_TIMEOUT, "upstream timed out")

    assert error.code == ErrorCode.SOURCE_TIMEOUT
    assert str(error) == "upstream timed out"

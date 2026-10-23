from __future__ import annotations

import pytest

from ai4i.data import (
    DEFAULT_DATA_PATH,
    EXPECTED_SHA256,
    DataValidationError,
    read_checksum_file,
    sha256_file,
)
from ai4i.download import download_dataset


def test_download_copies_and_verifies_data(tmp_path) -> None:
    target = tmp_path / "ai4i2020.csv"
    checksum = tmp_path / "SHA256SUMS"

    result = download_dataset(target, checksum, url=DEFAULT_DATA_PATH.as_uri())

    assert result["status"] == "downloaded"
    assert sha256_file(target) == EXPECTED_SHA256
    assert read_checksum_file(checksum) == EXPECTED_SHA256


def test_download_rejects_bad_checksum(tmp_path) -> None:
    source = tmp_path / "not_ai4i.csv"
    source.write_bytes(b"this is not the dataset")
    target = tmp_path / "ai4i2020.csv"

    with pytest.raises(DataValidationError):
        download_dataset(
            target,
            tmp_path / "SHA256SUMS",
            url=source.as_uri(),
        )

    assert not target.exists()


def test_existing_wrong_file_requires_force(tmp_path) -> None:
    target = tmp_path / "ai4i2020.csv"
    target.write_bytes(b"stale data")
    checksum = tmp_path / "SHA256SUMS"

    with pytest.raises(DataValidationError):
        download_dataset(target, checksum, url=DEFAULT_DATA_PATH.as_uri())

    result = download_dataset(
        target,
        checksum,
        url=DEFAULT_DATA_PATH.as_uri(),
        force=True,
    )

    assert result["status"] == "downloaded"
    assert sha256_file(target) == EXPECTED_SHA256

from __future__ import annotations

import json

import pandas as pd
import pytest

from ai4i.data import (
    DEFAULT_CHECKSUM_PATH,
    DEFAULT_DATA_PATH,
    EXPECTED_COLUMNS,
    EXPECTED_FAILURE_COUNT,
    EXPECTED_FAILURE_WITHOUT_MODE,
    EXPECTED_MODE_COUNTS,
    EXPECTED_MODE_WITHOUT_FAILURE,
    EXPECTED_MULTIPLE_MODE_ROWS,
    EXPECTED_ROWS,
    EXPECTED_SHA256,
    EXPECTED_TYPE_COUNTS,
    FAILURE_MODE_COLUMNS,
    PHYSICAL_BOUNDS,
    TARGET_COLUMN,
    load_raw,
    read_checksum_file,
    sha256_file,
    validate_dataframe,
    validate_dataset,
)
from ai4i.validate_data import main


@pytest.fixture(scope="session")
def df() -> pd.DataFrame:
    return load_raw()


def test_raw_file_exists() -> None:
    assert DEFAULT_DATA_PATH.is_file()


def test_checksum_matches_pinned_value() -> None:
    assert sha256_file(DEFAULT_DATA_PATH) == EXPECTED_SHA256


def test_checksum_file_matches_pinned_value() -> None:
    assert read_checksum_file(DEFAULT_CHECKSUM_PATH) == EXPECTED_SHA256


def test_shape_and_column_order(df: pd.DataFrame) -> None:
    assert df.shape == (EXPECTED_ROWS, len(EXPECTED_COLUMNS))
    assert list(df.columns) == EXPECTED_COLUMNS


def test_no_missing_or_duplicate_rows(df: pd.DataFrame) -> None:
    assert not df.isna().any().any()
    assert not df.duplicated().any()


def test_identifiers_are_unique_and_contiguous(df: pd.DataFrame) -> None:
    assert df["UDI"].is_unique
    assert df["UDI"].tolist() == list(range(1, EXPECTED_ROWS + 1))
    assert df["Product ID"].is_unique
    assert (df["Product ID"].astype("string").str.strip() != "").all()


def test_type_values_and_counts(df: pd.DataFrame) -> None:
    assert set(df["Type"]) <= {"L", "M", "H"}
    assert df["Type"].value_counts().to_dict() == EXPECTED_TYPE_COUNTS


def test_binary_columns(df: pd.DataFrame) -> None:
    for column in [TARGET_COLUMN, *FAILURE_MODE_COLUMNS]:
        assert set(df[column].unique()) <= {0, 1}


def test_known_failure_counts(df: pd.DataFrame) -> None:
    assert int(df[TARGET_COLUMN].sum()) == EXPECTED_FAILURE_COUNT
    assert {
        column: int(df[column].sum()) for column in FAILURE_MODE_COLUMNS
    } == EXPECTED_MODE_COUNTS


def test_numeric_columns_within_physical_bounds(df: pd.DataFrame) -> None:
    for column, (lower, upper) in PHYSICAL_BOUNDS.items():
        assert float(df[column].min()) >= lower
        assert float(df[column].max()) <= upper


def test_documented_failure_label_inconsistencies(df: pd.DataFrame) -> None:
    any_mode = df[FAILURE_MODE_COLUMNS].any(axis=1)

    assert int((~any_mode & (df[TARGET_COLUMN] == 1)).sum()) == EXPECTED_FAILURE_WITHOUT_MODE
    assert int((any_mode & (df[TARGET_COLUMN] == 0)).sum()) == EXPECTED_MODE_WITHOUT_FAILURE
    assert (
        int((df[FAILURE_MODE_COLUMNS].sum(axis=1) > 1).sum())
        == EXPECTED_MULTIPLE_MODE_ROWS
    )


def test_clean_dataframe_passes_validation(df: pd.DataFrame) -> None:
    assert validate_dataframe(df) == []


def test_validate_dataset_report() -> None:
    report = validate_dataset()

    assert report["valid"] is True
    assert report["errors"] == []
    assert report["checksum_ok"] is True
    assert report["checksum_file_ok"] is True
    assert report["rows"] == EXPECTED_ROWS
    assert report["failure_count"] == EXPECTED_FAILURE_COUNT
    assert report["mode_counts"] == EXPECTED_MODE_COUNTS
    assert report["type_counts"] == EXPECTED_TYPE_COUNTS
    assert report["consistency"]["failure_without_mode"] == EXPECTED_FAILURE_WITHOUT_MODE
    assert report["consistency"]["mode_without_failure"] == EXPECTED_MODE_WITHOUT_FAILURE
    assert report["consistency"]["multiple_mode_rows"] == EXPECTED_MULTIPLE_MODE_ROWS


def test_detects_missing_column(tmp_path, df: pd.DataFrame) -> None:
    bad_path = tmp_path / "missing_torque.csv"
    df.drop(columns=["Torque [Nm]"]).to_csv(bad_path, index=False)

    report = validate_dataset(bad_path, verify_checksum=False)

    assert report["valid"] is False
    assert any("Torque [Nm]" in error for error in report["errors"])


def test_detects_out_of_range_values(tmp_path, df: pd.DataFrame) -> None:
    bad = df.copy()
    bad.loc[0, "Torque [Nm]"] = -1.0
    bad_path = tmp_path / "bad_torque.csv"
    bad.to_csv(bad_path, index=False)

    report = validate_dataset(bad_path, verify_checksum=False)

    assert report["valid"] is False
    assert any("Torque [Nm]" in error and "合理範圍" in error for error in report["errors"])


def test_detects_invalid_binary_values(tmp_path, df: pd.DataFrame) -> None:
    bad = df.copy()
    bad.loc[0, TARGET_COLUMN] = 2
    bad_path = tmp_path / "bad_target.csv"
    bad.to_csv(bad_path, index=False)

    report = validate_dataset(bad_path, verify_checksum=False)

    assert report["valid"] is False
    assert any(TARGET_COLUMN in error for error in report["errors"])


def test_cli_writes_report(tmp_path) -> None:
    output = tmp_path / "data_validation.json"

    assert main(["--json-out", str(output)]) == 0

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["valid"] is True
    assert report["checksum_ok"] is True


def test_cli_returns_nonzero_for_bad_data(tmp_path, df: pd.DataFrame) -> None:
    bad_path = tmp_path / "bad.csv"
    df.drop(columns=["Type"]).to_csv(bad_path, index=False)
    output = tmp_path / "bad_report.json"

    assert (
        main(
            [
                "--data-path",
                str(bad_path),
                "--json-out",
                str(output),
                "--no-checksum",
            ]
        )
        == 1
    )
    assert output.is_file()

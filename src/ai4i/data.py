"""Data loading and validation for the AI4I 2020 dataset.

The raw CSV is treated as immutable. Validation failures are reported as
structured errors instead of silently repairing the data.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "ai4i2020.csv"
DEFAULT_CHECKSUM_PATH = PROJECT_ROOT / "data" / "raw" / "SHA256SUMS"
DEFAULT_REPORT_PATH = PROJECT_ROOT / "reports" / "data_validation.json"

# Pinned checksum of the UCI CSV (archive.ics.uci.edu/ml/machine-learning-databases/00601/ai4i2020.csv).
EXPECTED_SHA256 = "dc6630cd9b1f0f853922fad78a1b6436570d3f1ec863f1dd5c4340ac56bc8a8e"
EXPECTED_ROWS = 10_000

EXPECTED_COLUMNS = [
    "UDI",
    "Product ID",
    "Type",
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]",
    "Machine failure",
    "TWF",
    "HDF",
    "PWF",
    "OSF",
    "RNF",
]

NUMERIC_COLUMNS = [
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]",
]

TARGET_COLUMN = "Machine failure"
FAILURE_MODE_COLUMNS = ["TWF", "HDF", "PWF", "OSF", "RNF"]
BINARY_COLUMNS = [TARGET_COLUMN, *FAILURE_MODE_COLUMNS]
CATEGORICAL_COLUMNS = ["Type"]
IDENTIFIER_COLUMNS = ["UDI", "Product ID"]

EXPECTED_FAILURE_COUNT = 339
EXPECTED_MODE_COUNTS = {"TWF": 46, "HDF": 115, "PWF": 95, "OSF": 98, "RNF": 19}
EXPECTED_TYPE_COUNTS = {"L": 6000, "M": 2997, "H": 1003}
EXPECTED_FAILURE_WITHOUT_MODE = 9
EXPECTED_MODE_WITHOUT_FAILURE = 18
EXPECTED_MULTIPLE_MODE_ROWS = 24

# Broad physical bounds used for sanity checks. Observed values are documented
# in docs/data_dictionary.md; these bounds only catch clearly invalid data.
PHYSICAL_BOUNDS: dict[str, tuple[float, float]] = {
    "Air temperature [K]": (250.0, 350.0),
    "Process temperature [K]": (250.0, 400.0),
    "Rotational speed [rpm]": (0.0, 10_000.0),
    "Torque [Nm]": (0.0, 200.0),
    "Tool wear [min]": (0.0, 1_000.0),
}


class DataValidationError(RuntimeError):
    """Raised when the dataset or checksum file cannot be validated."""


def sha256_file(path: str | Path) -> str:
    """Return the lowercase SHA-256 checksum of a file."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_checksum_file(path: str | Path = DEFAULT_CHECKSUM_PATH) -> str:
    """Read the expected checksum for ai4i2020.csv from a SHA256SUMS file."""

    checksum_path = Path(path)
    if not checksum_path.is_file():
        raise FileNotFoundError(f"找不到 checksum 檔：{checksum_path}")

    filename = DEFAULT_DATA_PATH.name
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1].lstrip("*") == filename:
            return parts[0].lower()
    raise DataValidationError(f"checksum 檔中找不到 {filename}：{checksum_path}")


def load_raw(path: str | Path = DEFAULT_DATA_PATH) -> pd.DataFrame:
    """Load the immutable raw CSV."""

    data_path = Path(path)
    if not data_path.is_file():
        raise FileNotFoundError(f"找不到原始資料檔：{data_path}")
    return pd.read_csv(data_path)


def validate_dataframe(df: pd.DataFrame) -> list[str]:
    """Validate schema, types, ranges and data quality invariants.

    Returns a list of human-readable errors. An empty list means the data
    passed every check.
    """

    errors: list[str] = []

    missing_columns = [column for column in EXPECTED_COLUMNS if column not in df.columns]
    unexpected_columns = [column for column in df.columns if column not in EXPECTED_COLUMNS]
    if missing_columns:
        errors.append(f"缺少必要欄位：{', '.join(missing_columns)}")
    if unexpected_columns:
        errors.append(f"出現未預期欄位：{', '.join(unexpected_columns)}")
    if missing_columns:
        return errors

    if list(df.columns) != EXPECTED_COLUMNS:
        errors.append("欄位順序與預期 schema 不一致")

    if len(df) != EXPECTED_ROWS:
        errors.append(f"資料筆數應為 {EXPECTED_ROWS}，實際為 {len(df)}")

    missing_values = int(df.isna().sum().sum())
    if missing_values:
        errors.append(f"發現 {missing_values} 個缺失值")

    duplicate_rows = int(df.duplicated().sum())
    if duplicate_rows:
        errors.append(f"發現 {duplicate_rows} 筆完全重複的資料列")

    if not df["UDI"].is_unique:
        errors.append("UDI 不是唯一值")
    if not df["UDI"].between(1, EXPECTED_ROWS).all():
        errors.append(f"UDI 必須介於 1 與 {EXPECTED_ROWS} 之間")

    if not df["Product ID"].is_unique:
        errors.append("Product ID 不是唯一值")
    if (df["Product ID"].astype("string").str.strip() == "").any():
        errors.append("Product ID 存在空白值")

    invalid_types = sorted(set(df["Type"]) - {"L", "M", "H"})
    if invalid_types:
        errors.append(f"Type 出現未定義值：{invalid_types}")

    for column in NUMERIC_COLUMNS:
        if not pd.api.types.is_numeric_dtype(df[column]):
            errors.append(f"{column} 必須為數值欄位")

    for column in BINARY_COLUMNS:
        if not pd.api.types.is_integer_dtype(df[column]):
            errors.append(f"{column} 必須為整數欄位")
        elif not df[column].isin([0, 1]).all():
            errors.append(f"{column} 只能包含 0 或 1")

    for column, (lower, upper) in PHYSICAL_BOUNDS.items():
        minimum = float(df[column].min())
        maximum = float(df[column].max())
        if minimum < lower or maximum > upper:
            errors.append(
                f"{column} 超出合理範圍 [{lower}, {upper}]：實際 [{minimum}, {maximum}]"
            )

    return errors


def _failure_mode_consistency(df: pd.DataFrame) -> dict[str, int] | None:
    if not all(column in df.columns for column in FAILURE_MODE_COLUMNS):
        return None
    if TARGET_COLUMN not in df.columns:
        return None

    any_mode = df[FAILURE_MODE_COLUMNS].any(axis=1)
    return {
        "failure_without_mode": int((~any_mode & (df[TARGET_COLUMN] == 1)).sum()),
        "mode_without_failure": int((any_mode & (df[TARGET_COLUMN] == 0)).sum()),
        "multiple_mode_rows": int((df[FAILURE_MODE_COLUMNS].sum(axis=1) > 1).sum()),
    }


def _display_path(path: str | Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(resolved)


def build_report(
    df: pd.DataFrame,
    data_path: str | Path = DEFAULT_DATA_PATH,
    *,
    checksum_actual: str | None = None,
    checksum_file_expected: str | None = None,
    checksum_verified: bool = True,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    """Build a JSON-serialisable validation report."""

    report: dict[str, Any] = {
        "path": _display_path(data_path),
        "sha256": checksum_actual,
        "sha256_expected": EXPECTED_SHA256,
        "sha256_file": checksum_file_expected,
        "checksum_verified": checksum_verified,
        "checksum_ok": (
            checksum_actual == EXPECTED_SHA256 if checksum_actual is not None else None
        ),
        "checksum_file_ok": (
            checksum_file_expected == checksum_actual
            if checksum_actual is not None and checksum_file_expected is not None
            else None
        ),
        "rows": len(df),
        "columns": int(df.shape[1]),
        "column_names": list(df.columns),
        "missing_values": int(df.isna().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
        "duplicate_udi": int(df["UDI"].duplicated().sum()) if "UDI" in df.columns else None,
        "duplicate_product_id": (
            int(df["Product ID"].duplicated().sum()) if "Product ID" in df.columns else None
        ),
        "type_counts": (
            {str(key): int(value) for key, value in df["Type"].value_counts().items()}
            if "Type" in df.columns
            else None
        ),
        "failure_count": (
            int(df[TARGET_COLUMN].sum()) if TARGET_COLUMN in df.columns else None
        ),
        "failure_rate": (
            round(float(df[TARGET_COLUMN].mean()), 6)
            if TARGET_COLUMN in df.columns and len(df)
            else None
        ),
        "mode_counts": {
            column: int(df[column].sum())
            for column in FAILURE_MODE_COLUMNS
            if column in df.columns
        },
        "numeric_ranges": {
            column: {
                "min": float(df[column].min()),
                "max": float(df[column].max()),
                "mean": round(float(df[column].mean()), 6),
            }
            for column in NUMERIC_COLUMNS
            if column in df.columns
        },
        "consistency": _failure_mode_consistency(df),
        "warnings": [],
        "errors": list(errors or []),
    }

    consistency = report["consistency"]
    if consistency:
        if consistency["failure_without_mode"]:
            report["warnings"].append(
                f"{consistency['failure_without_mode']} 筆 Machine failure=1 但五種故障模式皆為 0"
            )
        if consistency["mode_without_failure"]:
            report["warnings"].append(
                f"{consistency['mode_without_failure']} 筆故障模式=1 但 Machine failure=0"
            )
        if consistency["multiple_mode_rows"]:
            report["warnings"].append(
                f"{consistency['multiple_mode_rows']} 筆同時有多種故障模式"
            )

    report["valid"] = not report["errors"]
    return report


def validate_dataset(
    data_path: str | Path = DEFAULT_DATA_PATH,
    checksum_path: str | Path = DEFAULT_CHECKSUM_PATH,
    *,
    verify_checksum: bool = True,
) -> dict[str, Any]:
    """Validate the raw dataset and return a structured report."""

    path = Path(data_path)
    df = load_raw(path)
    errors = validate_dataframe(df)
    checksum_actual = sha256_file(path)
    checksum_file_expected: str | None = None

    if verify_checksum:
        if checksum_actual != EXPECTED_SHA256:
            errors.append(
                f"SHA-256 與釘選值不符：實際 {checksum_actual}，預期 {EXPECTED_SHA256}"
            )
        try:
            checksum_file_expected = read_checksum_file(checksum_path)
        except (FileNotFoundError, DataValidationError) as exc:
            errors.append(str(exc))
        else:
            if checksum_file_expected != EXPECTED_SHA256:
                errors.append(
                    f"checksum 檔內容與釘選值不符：{checksum_file_expected} != {EXPECTED_SHA256}"
                )

    report = build_report(
        df,
        path,
        checksum_actual=checksum_actual,
        checksum_file_expected=checksum_file_expected,
        checksum_verified=verify_checksum,
        errors=errors,
    )
    report["valid"] = not errors
    return report


def write_report(report: dict[str, Any], path: str | Path = DEFAULT_REPORT_PATH) -> Path:
    """Write a validation report as UTF-8 JSON."""

    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report_path

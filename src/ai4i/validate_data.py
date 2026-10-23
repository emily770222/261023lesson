"""Command-line entry point for raw data validation."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from ai4i.data import (
    DEFAULT_CHECKSUM_PATH,
    DEFAULT_DATA_PATH,
    DEFAULT_REPORT_PATH,
    DataValidationError,
    validate_dataset,
    write_report,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the AI4I 2020 raw dataset and write a JSON report."
    )
    parser.add_argument(
        "--data-path",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help=f"raw CSV path (default: {DEFAULT_DATA_PATH})",
    )
    parser.add_argument(
        "--checksum-path",
        type=Path,
        default=DEFAULT_CHECKSUM_PATH,
        help=f"SHA256SUMS path (default: {DEFAULT_CHECKSUM_PATH})",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help=f"report output path (default: {DEFAULT_REPORT_PATH})",
    )
    parser.add_argument(
        "--no-checksum",
        action="store_true",
        help="skip checksum verification (for deliberately modified test data)",
    )
    args = parser.parse_args(argv)

    try:
        report = validate_dataset(
            args.data_path,
            args.checksum_path,
            verify_checksum=not args.no_checksum,
        )
    except (FileNotFoundError, DataValidationError) as exc:
        print(f"資料驗證失敗：{exc}", file=sys.stderr)
        return 1

    report_path = write_report(report, args.json_out)

    print(f"資料檔：{report['path']}")
    print(f"維度：{report['rows']} 列 × {report['columns']} 欄")
    print(f"SHA-256：{report['sha256']}")
    if report["checksum_verified"]:
        checksum_status = "通過" if report["checksum_ok"] else "未通過"
    else:
        checksum_status = "略過"
    print(f"checksum 驗證：{checksum_status}")
    if report["failure_count"] is not None:
        print(
            f"故障筆數：{report['failure_count']} "
            f"({report['failure_rate']:.2%})"
        )
    if report["mode_counts"]:
        modes = "、".join(f"{key}={value}" for key, value in report["mode_counts"].items())
        print(f"故障模式：{modes}")

    for warning in report["warnings"]:
        print(f"注意：{warning}")

    if not report["valid"]:
        for error in report["errors"]:
            print(f"錯誤：{error}", file=sys.stderr)
        print(f"報告已寫入：{report_path}", file=sys.stderr)
        return 1

    print(f"驗證通過，報告已寫入：{report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

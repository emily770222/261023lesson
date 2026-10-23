"""Download the canonical AI4I 2020 CSV and verify its checksum."""

from __future__ import annotations

import argparse
import hashlib
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from ai4i.data import (
    DEFAULT_CHECKSUM_PATH,
    DEFAULT_DATA_PATH,
    EXPECTED_SHA256,
    DataValidationError,
    sha256_file,
)

DATASET_URL = (
    "https://archive.ics.uci.edu/ml/machine-learning-databases/00601/ai4i2020.csv"
)


def _write_checksum_file(path: Path, digest: str, filename: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{digest}  {filename}\n", encoding="ascii", newline="\n")


def download_dataset(
    target: str | Path = DEFAULT_DATA_PATH,
    checksum_path: str | Path = DEFAULT_CHECKSUM_PATH,
    *,
    url: str = DATASET_URL,
    force: bool = False,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """Download the dataset, verifying the pinned SHA-256 before writing."""

    target_path = Path(target)
    checksum_file = Path(checksum_path)

    if target_path.is_file():
        existing_digest = sha256_file(target_path)
        if existing_digest == EXPECTED_SHA256:
            _write_checksum_file(checksum_file, existing_digest, target_path.name)
            return {
                "status": "already_present",
                "path": str(target_path),
                "sha256": existing_digest,
            }
        if not force:
            raise DataValidationError(
                f"目標檔已存在但 checksum 不符：{target_path}。"
                "確認要覆蓋時請加上 --force。"
            )

    with urlopen(url, timeout=timeout) as response:
        payload = response.read()

    digest = hashlib.sha256(payload).hexdigest()
    if digest != EXPECTED_SHA256:
        raise DataValidationError(
            f"下載檔案的 SHA-256 不符：實際 {digest}，預期 {EXPECTED_SHA256}"
        )

    target_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = target_path.with_name(target_path.name + ".tmp")
    try:
        temporary_path.write_bytes(payload)
        temporary_path.replace(target_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    _write_checksum_file(checksum_file, digest, target_path.name)
    return {"status": "downloaded", "path": str(target_path), "sha256": digest}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Download the AI4I 2020 raw CSV and verify its checksum."
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help=f"destination CSV (default: {DEFAULT_DATA_PATH})",
    )
    parser.add_argument(
        "--checksum-path",
        type=Path,
        default=DEFAULT_CHECKSUM_PATH,
        help=f"SHA256SUMS output (default: {DEFAULT_CHECKSUM_PATH})",
    )
    parser.add_argument("--url", default=DATASET_URL, help="source URL")
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing file whose checksum does not match",
    )
    args = parser.parse_args(argv)

    try:
        result = download_dataset(
            args.target,
            args.checksum_path,
            url=args.url,
            force=args.force,
        )
    except (OSError, DataValidationError) as exc:
        print(f"下載失敗：{exc}", file=sys.stderr)
        return 1

    if result["status"] == "already_present":
        print(f"資料已存在且 checksum 正確：{result['path']}")
    else:
        print(f"已下載並驗證：{result['path']}")
    print(f"SHA-256：{result['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

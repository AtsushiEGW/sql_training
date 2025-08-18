#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Load all CSV files under work/data into Postgres.
- Table name = CSV filename (without extension), sanitized to snake_case.
- Uses environment variables (PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE).
- Defaults for Docker: db:5432 / postgres:postgres / postgres
- CLI options:
    --data-dir PATH     (default: work/data next to this file)
    --schema NAME       (default: public)
    --if-exists {fail,replace,append}  (default: append)
    --chunksize N       (default: 50_000)
Usage:
    python init.py
    python init.py --schema raw --if-exists replace
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# ---------- Config helpers ----------

def env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    return v if v not in (None, "") else default

def build_sqlalchemy_url() -> str:
    host = env("POSTGRES_HOST", "db")            # docker-compose のサービス名を想定
    port = env("POSTGRES_PORT", "5432")
    user = env("POSTGRES_USER", "postgres")
    password = env("POSTGRES_PASSWORD", "postgres")
    database = env("POSTGRES_DB", "postgres")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"

# ---------- Path helpers ----------

def default_data_dir() -> Path:
    # プロジェクトルート/ work / data を想定
    return (Path(__file__).resolve().parent / "work" / "data").resolve()

# ---------- Table name sanitization ----------

_reserved = {
    "user", "order", "select", "table", "group", "where", "from", "to", "by",
    "limit", "offset", "primary", "foreign", "values", "timestamp"
}

def sanitize_table_name(name: str) -> str:
    """
    - lower
    - replace non [a-z0-9_] with _
    - collapse multiple _
    - trim leading/trailing _
    - prefix with t_ if starts with digit or reserved word
    """
    base = name.lower()
    base = re.sub(r"[^a-z0-9_]+", "_", base)
    base = re.sub(r"_+", "_", base).strip("_")
    if not base:
        base = "table"
    if base[0].isdigit() or base in _reserved:
        base = f"t_{base}"
    return base

# ---------- CSV readers ----------

def iter_csv_files(data_dir: Path) -> Iterable[Path]:
    for p in sorted(data_dir.glob("*.csv")):
        if p.is_file():
            yield p

def read_csv_with_fallback(path: Path) -> pd.DataFrame:
    """
    まず UTF-8, 失敗したら CP932(Shift-JIS) で再試行。
    dtype は pandas に任せ、巨大ファイルはメモリ効率のために low_memory=True。
    """
    try:
        return pd.read_csv(path, low_memory=True)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="cp932", low_memory=True)

# ---------- Loader ----------

def ensure_schema(engine: Engine, schema: str) -> None:
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))

def load_one_csv(
    engine: Engine,
    csv_path: Path,
    schema: str,
    if_exists: str = "append",
    chunksize: int = 50_000,
) -> str:
    table = sanitize_table_name(csv_path.stem)
    df = read_csv_with_fallback(csv_path)

    # 列名サニタイズ（Postgres の識別子として安全に）
    df.columns = [sanitize_table_name(str(c)) for c in df.columns]

    # pandas 2.0+: method="multi" でバルク挿入
    df.to_sql(
        name=table,
        con=engine,
        schema=schema,
        if_exists=if_exists,         # 'fail' | 'replace' | 'append'
        index=False,
        method="multi",
        chunksize=chunksize,
    )
    return table

# ---------- CLI / main ----------

def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load CSVs in work/data to Postgres")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=default_data_dir(),
        help="Directory containing CSV files (default: work/data)",
    )
    parser.add_argument(
        "--schema",
        type=str,
        default="public",
        help="Target schema (default: public)",
    )
    parser.add_argument(
        "--if-exists",
        choices=("fail", "replace", "append"),
        default="append",
        help="Behavior if table exists (default: append)",
    )
    parser.add_argument(
        "--chunksize",
        type=int,
        default=50_000,
        help="Rows per insert batch (default: 50000)",
    )
    return parser.parse_args(argv)

def main(argv: list[str]) -> int:
    args = parse_args(argv)
    data_dir: Path = args.data_dir

    if not data_dir.exists():
        print(f"[ERROR] Data directory not found: {data_dir}", file=sys.stderr)
        return 1

    url = build_sqlalchemy_url()
    engine = create_engine(url, future=True)

    # スキーマ作成
    ensure_schema(engine, args.schema)

    csvs = list(iter_csv_files(data_dir))
    if not csvs:
        print(f"[INFO] No CSV files found in: {data_dir}")
        return 0

    print(f"[INFO] Target schema: {args.schema}")
    print(f"[INFO] Loading {len(csvs)} file(s) from {data_dir} ...")

    for i, csv_path in enumerate(csvs, 1):
        try:
            table = load_one_csv(
                engine=engine,
                csv_path=csv_path,
                schema=args.schema,
                if_exists=args.if_exists,
                chunksize=args.chunksize,
            )
            print(f"[{i}/{len(csvs)}] Loaded {csv_path.name} -> {args.schema}.{table}", end="\r")
        except Exception as e:
            print(f"[ERROR] Failed to load {csv_path.name}: {e}", file=sys.stderr)
            return 2

    print("[DONE] All CSVs loaded successfully.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
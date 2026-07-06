"""DuckDB を初期化し、data/ 配下の CSV を取り込むスクリプト。

使い方:
    uv run python init.py

データの配置ルール:
    data/<スキーマ名>/<テーブル名>.csv
      - data/ 直下のフォルダ名 -> DuckDB のスキーマ名
      - その中の CSV のファイル名（拡張子なし） -> テーブル名

処理の流れ:
    1. db/learning.duckdb を作成
    2. data/ 内の各スキーマフォルダを走査し、スキーマを作成
    3. 各フォルダ内の *.csv を "スキーマ名"."テーブル名" として取り込む
    4. init.sql があれば実行（ビューなど SQL レベルの追加セットアップ用）
    5. 取り込み結果を表示

なぜ CSV 取り込みが Python なのか:
    「フォルダとファイルを走査して、フォルダ名でスキーマ・ファイル名でテーブルを作る」
    にはループ処理が必要で、純粋な SQL では書けないため。
    SQL で書きたい追加処理（結合ビューの定義など）は init.sql に記述する。
"""

from __future__ import annotations

from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
DB_DIR = PROJECT_ROOT / "db"
DB_PATH = DB_DIR / "learning.duckdb"
INIT_SQL = PROJECT_ROOT / "init.sql"


def load_schemas(con: duckdb.DuckDBPyConnection) -> list[tuple[str, str]]:
    """data/ 内の各フォルダをスキーマ、その中の CSV をテーブルとして取り込む。

    Returns:
        取り込んだ (スキーマ名, テーブル名) のリスト。
    """
    loaded: list[tuple[str, str]] = []
    for schema_dir in sorted(p for p in DATA_DIR.iterdir() if p.is_dir()):
        schema = schema_dir.name
        con.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
        for csv_path in sorted(schema_dir.glob("*.csv")):
            table = csv_path.stem  # 例: data/hr/employees.csv -> "employees"
            safe_path = str(csv_path).replace("'", "''")  # パスの ' をエスケープ
            con.execute(
                f'CREATE OR REPLACE TABLE "{schema}"."{table}" AS '
                f"SELECT * FROM read_csv_auto('{safe_path}')"
            )
            loaded.append((schema, table))
    return loaded


def main() -> None:
    if not DATA_DIR.exists():
        raise SystemExit(f"data ディレクトリが見つかりません: {DATA_DIR}")

    # data/ 直下に置かれた CSV は、どのスキーマにも属さないため取り込まれない
    stray = sorted(DATA_DIR.glob("*.csv"))
    if stray:
        print("注意: data/ 直下の CSV はスキーマフォルダに属さないため取り込みません:")
        for p in stray:
            print(f"  - {p.name}（data/<スキーマ名>/ の中へ移動してください）")

    DB_DIR.mkdir(exist_ok=True)

    con = duckdb.connect(str(DB_PATH))
    try:
        loaded = load_schemas(con)
        if not loaded:
            print("警告: 取り込める CSV が見つかりませんでした。")

        # SQL レベルの追加セットアップ（任意・空でも可）
        if INIT_SQL.exists() and INIT_SQL.read_text(encoding="utf-8").strip():
            con.execute(INIT_SQL.read_text(encoding="utf-8"))

        print(f"\nDB を作成しました: {DB_PATH.relative_to(PROJECT_ROOT)}")
        print("取り込んだテーブル（スキーマ別）:")
        current_schema = None
        for schema, table in loaded:
            if schema != current_schema:
                print(f"  [{schema}]")
                current_schema = schema
            count = con.execute(
                f'SELECT COUNT(*) FROM "{schema}"."{table}"'
            ).fetchone()[0]
            print(f"    - {table} ({count} 行)")
    finally:
        con.close()


if __name__ == "__main__":
    main()

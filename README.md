# SQL Learning (DuckDB + marimo)

DuckDB と marimo を使った、ローカル完結の SQL 学習環境です。
`data/` の中を **プロジェクト（スキーマ）単位のフォルダ**で分け、複数プロジェクトを
1つの DuckDB にまとめて取り込みます。

## データの配置ルール

```
data/<スキーマ名>/<テーブル名>.csv
```

- `data/` 直下のフォルダ名 … DuckDB の **スキーマ名** になる
- その中の CSV のファイル名（拡張子なし） … **テーブル名** になる

例）`data/hr/employees.csv` -> テーブル `hr.employees`

## ディレクトリ構成

```
sql-learning/
├── pyproject.toml      # uv 用のプロジェクト設定（依存: duckdb / marimo / polars）
├── .python-version
├── .gitignore
├── README.md
├── init.py             # DB 作成 + data/ 配下の全スキーマ・全CSVを取り込み
├── init.sql            # 取り込み後の SQL セットアップ（結合ビューなど）
├── data/               # 取り込み元。スキーマフォルダごとに CSV を置く
│   ├── ecommerce/
│   │   ├── customers.csv
│   │   ├── products.csv
│   │   ├── orders.csv
│   │   └── order_items.csv
│   └── hr/
│       ├── departments.csv
│       └── employees.csv
├── db/                 # init.py が生成（gitignore 済み）
│   └── learning.duckdb
└── learning/           # 学習用の marimo ノート
    └── 01_basics.py
```

## 使い方

### 1. 環境構築

```bash
uv sync
```

### 2. データを DuckDB に取り込む

```bash
uv run python init.py
```

`data/` 内の各スキーマフォルダを走査し、フォルダ名でスキーマを、
その中の各 CSV でテーブルを作成して `db/learning.duckdb` に取り込みます。
続けて `init.sql` を実行し、`ecommerce.order_details` ビューを作成します。

スキーマ（フォルダ）や CSV を追加・変更したら `init.py` を再実行すれば作り直せます。

### 3. 学習ノートを開く

```bash
uv run marimo edit learning/01_basics.py
```

## 仕組みのメモ

- **取り込みが Python（init.py）なのはなぜ？**
  「フォルダとファイルを走査して、フォルダ名でスキーマ・ファイル名でテーブルを作る」
  にはループ処理が必要で、純粋な SQL では書けないためです。
  SQL で書きたい追加処理（ビュー定義など）は `init.sql` に記述します。

- **テーブルの参照方法**
  `スキーマ名.テーブル名`（例: `ecommerce.orders`）で参照します。
  ノートでは `USE ecommerce;` で既定スキーマを設定しているため、`ecommerce` 内は
  非修飾で書け、別スキーマは `hr.employees` のように修飾して参照します。

- **ノートは読み取り専用で接続**しています（`read_only=True`）。
  `init.py` で作り直すときは、開いている marimo を先に閉じてください
  （DuckDB のファイルは同時に書き込めるプロセスが1つに限られるため）。

- **data/ 直下に置いた CSV は取り込まれません**（どのスキーマにも属さないため）。
  init.py が実行時に警告を出します。必ずスキーマフォルダの中へ置いてください。

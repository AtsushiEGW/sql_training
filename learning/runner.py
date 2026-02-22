from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Union, Literal
import hashlib
import re
import datetime

import pandas as pd
import numpy as np
import marimo as mo  # marimo をインポート

import psycopg
import duckdb

# =============================================================================
# SQL preprocessing / splitting (変更なし)
# =============================================================================

_LINE_COMMENT_RE = re.compile(r"--.*?$", flags=re.M)
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", flags=re.S)

def strip_sql_comments(sql: str) -> str:
    sql = _BLOCK_COMMENT_RE.sub("", sql)
    sql = _LINE_COMMENT_RE.sub("", sql)
    return sql

def split_sql_statements(sql: str) -> list[str]:
    cleaned = strip_sql_comments(sql)
    parts = [s.strip() for s in cleaned.strip().split(";")]
    return [p for p in parts if p]

# =============================================================================
# DataFrame normalization / hashing (変更なし)
# =============================================================================

_COL_SEP = "\x1f"
_ROW_SEP = "\n"
_NULL = "<NULL>"

def normalize_df_shape(df: pd.DataFrame, *, ignore_col_order: bool = True) -> pd.DataFrame:
    out = df.copy()
    if ignore_col_order:
        out = out.reindex(sorted(out.columns), axis=1)
    return out.reset_index(drop=True)

def sort_rows_stably(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.reset_index(drop=True)
    try:
        return df.sort_values(by=list(df.columns), kind="mergesort").reset_index(drop=True)
    except Exception:
        tmp = df.copy()
        for c in tmp.columns:
            tmp[c] = tmp[c].astype(str)
        return tmp.sort_values(by=list(tmp.columns), kind="mergesort").reset_index(drop=True)

def _normalize_cell_for_text(x: Any, *, float_sig: int = 10) -> str:
    if x is None: return _NULL
    try:
        if pd.isna(x): return _NULL
    except Exception: pass
    if isinstance(x, pd.Timestamp):
        ts = x.tz_convert(None) if x.tzinfo else x
        if all(v == 0 for v in [ts.hour, ts.minute, ts.second, ts.microsecond]):
            return ts.date().isoformat()
        return ts.to_pydatetime().replace(tzinfo=None).isoformat(sep=" ", timespec="seconds")
    if isinstance(x, np.datetime64):
        ts = pd.to_datetime(x)
        if all(v == 0 for v in [ts.hour, ts.minute, ts.second, ts.microsecond]):
            return ts.date().isoformat()
        return ts.to_pydatetime().replace(tzinfo=None).isoformat(sep=" ", timespec="seconds")
    if isinstance(x, datetime.date) and not isinstance(x, datetime.datetime):
        return x.isoformat()
    if isinstance(x, datetime.datetime):
        dt = x.replace(tzinfo=None) if x.tzinfo else x
        if all(v == 0 for v in [dt.hour, dt.minute, dt.second, dt.microsecond]):
            return dt.date().isoformat()
        return dt.isoformat(sep=" ", timespec="seconds")
    if isinstance(x, (float, np.floating)):
        return format(float(x), f".{float_sig}g")
    return str(x)

def fingerprint_df(df: pd.DataFrame, *, ignore_row_order: bool = True, ignore_col_order: bool = True, algo: str = "sha256", float_sig: int = 10) -> str:
    x = df.copy()
    if ignore_col_order:
        x = x.reindex(sorted(x.columns), axis=1)
    row_strings: list[str] = []
    for row in x.itertuples(index=False, name=None):
        cells = [_normalize_cell_for_text(v, float_sig=float_sig) for v in row]
        row_strings.append(_COL_SEP.join(cells))
    if ignore_row_order:
        row_strings.sort()
    blob = _ROW_SEP.join(row_strings).encode("utf-8")
    h = hashlib.new(algo)
    h.update(blob)
    return h.hexdigest()

# =============================================================================
# Runner
# =============================================================================

Result = Union[pd.DataFrame, Dict[str, Any], None]
CompareMode = Literal["hash", "dataframe"]

@dataclass
class DualRunner:
    pg_conninfo: str
    duckdb_path: str = ":memory:"

    _pg: Optional[psycopg.Connection] = None
    _dd: Optional[duckdb.DuckDBPyConnection] = None

    def _get_pg(self) -> psycopg.Connection:
        if self._pg is None or self._pg.closed:
            self._pg = psycopg.connect(self.pg_conninfo)
        return self._pg

    def _get_dd(self) -> duckdb.DuckDBPyConnection:
        if self._dd is None:
            self._dd = duckdb.connect(self.duckdb_path)
        return self._dd

    # --- Jupyter/Marimo Display Helpers ---

    def pg(self, sql: str, params: Optional[Dict[str, Any]] = None) -> mo.Html:
        """Postgresのみ実行して結果を表示するコンポーネントを返す"""
        res = self.run_pg(sql, params)
        return mo.vstack([
            mo.md("### 🐘 PostgreSQL Result"),
            res
        ])

    def dd(self, sql: str, params: Optional[Dict[str, Any]] = None) -> mo.Html:
        """DuckDBのみ実行して結果を表示するコンポーネントを返す"""
        res = self.run_dd(sql, params)
        return mo.vstack([
            mo.md("### 🦆 DuckDB Result"),
            res
        ])

    # --- Execution Core (変更なし) ---

    def run_pg(self, sql: str, params: Optional[Dict[str, Any]] = None) -> Result:
        params = params or {}
        conn = self._get_pg()
        last_df = None
        executed = 0
        
        try:
            with conn.cursor() as cur:
                for stmt in split_sql_statements(sql):
                    executed += 1
                    cur.execute(stmt, params)
                    if cur.description is not None:
                        last_df = pd.DataFrame(cur.fetchall(), columns=[d.name for d in cur.description])
            conn.commit()  # すべて成功したらコミット
        except Exception as e:
            conn.rollback()  # エラーが起きたらロールバック
            raise e 

        return last_df if last_df is not None else {"ok": True, "executed": executed}


    def run_dd(self, sql: str, params: Optional[Dict[str, Any]] = None) -> Result:
        params = params or {}
        conn = self._get_dd()
        last_df = None
        executed = 0
        for stmt in split_sql_statements(sql):
            executed += 1
            res = conn.execute(stmt, params)
            try:
                df = res.df()
                if len(df.columns) > 0: last_df = df
            except Exception: pass
        return last_df if last_df is not None else {"ok": True, "executed": executed}

    # --- Comparison ---
    def check(
            self,
            sql: str,
            params: Optional[Dict[str, Any]] = None,
            *,
            mode: CompareMode = "hash",
            ignore_row_order: bool = True,
            ignore_col_order: bool = True,
            float_sig: int = 10,
            show_head: int = 10,
        ) -> mo.Html:
            """
            Marimo用に修正:
            結果を逐次 display() するのではなく、
            表示したい要素のリスト(mo.vstack)を返り値として戻す。
            """
            params = params or {}
            pg_out, dd_out = None, None
            pg_err, dd_err = None, None

            # 1. 両方のエンジンで実行
            try:
                pg_out = self.run_pg(sql, params)
            except Exception as e:
                pg_err = e

            try:
                dd_out = self.run_dd(sql, params)
            except Exception as e:
                dd_err = e

            # 表示要素を格納するリスト
            elements = []

            # 2. エラー発生時の処理
            if pg_err or dd_err:
                elements.append(mo.md("## ❌ Execution Error"))
                if pg_err:
                    elements.append(mo.callout(str(pg_err), kind="danger", title="🐘 PostgreSQL Error"))
                if dd_err:
                    elements.append(mo.callout(str(dd_err), kind="danger", title="🦆 DuckDB Error"))
                return mo.vstack(elements)

            # 3. SELECT/RETURNING がない場合の処理
            if not isinstance(pg_out, pd.DataFrame) or not isinstance(dd_out, pd.DataFrame):
                elements.append(mo.md("### ✅ No comparable result set (DDL/DML executed)"))
                elements.append(mo.ui.json(pg_out)) # 辞書などをきれいに表示
                return mo.vstack(elements)

            # 4. 比較ロジック
            pg_df = normalize_df_shape(pg_out, ignore_col_order=ignore_col_order)
            dd_df = normalize_df_shape(dd_out, ignore_col_order=ignore_col_order)

            same = False
            if mode == "hash":
                pg_fp = fingerprint_df(pg_df, ignore_row_order=ignore_row_order, float_sig=float_sig)
                dd_fp = fingerprint_df(dd_df, ignore_row_order=ignore_row_order, float_sig=float_sig)
                same = (pg_fp == dd_fp)
            else:
                pg_cmp = sort_rows_stably(pg_df) if ignore_row_order else pg_df
                dd_cmp = sort_rows_stably(dd_df) if ignore_row_order else dd_df
                try:
                    pd.testing.assert_frame_equal(pg_cmp, dd_cmp, check_dtype=False)
                    same = True
                except AssertionError:
                    same = False

            # 5. 結果の表示構築
            if same:
                elements.append(mo.md("### ✅ SAME"))
                # 一致していればPostgresの結果のみ表示
                elements.append(pg_out)
            else:
                elements.append(mo.md("## ❌ DIFF Detected"))
                
                # 型情報をデバッグ用に文字列化
                debug_info = f"**PG dtypes:**\n{pg_out.dtypes}\n\n**DuckDB dtypes:**\n{dd_out.dtypes}"
                
                # タブまたは並列表示で比較しやすくする
                elements.append(
                    mo.ui.tabs({
                        "🐘 PostgreSQL": pg_out,
                        "🦆 DuckDB": dd_out,
                        "🔍 Debug Info": mo.md(debug_info)
                    })
                )

            return mo.vstack(elements)

    def close(self) -> None:
        if self._pg: self._pg.close(); self._pg = None
        if self._dd: self._dd.close(); self._dd = None
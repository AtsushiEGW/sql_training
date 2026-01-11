"""
runner.py

Compare query results between Postgres (psycopg3) and DuckDB by executing the same SQL.

This module is intended for Jupyter workflows where you want to:
- run the same multi-statement SQL script on Postgres and DuckDB
- compare the final result set (SELECT / RETURNING) for equivalence
- print "same" or "diff" quickly
- optionally compare using a robust fingerprint hash for large result sets

Key features
------------
1) Multi-statement SQL support:
   - statements are separated by semicolons ';'
   - SQL comments are stripped before splitting:
        * line comment:  -- comment
        * block comment: /* comment */

2) Result-set capture:
   - the last statement that returns a result set (SELECT / RETURNING) is captured
   - returned as pandas.DataFrame

3) Comparison modes:
   - mode="hash" (default): normalize values -> hash rows -> compare fingerprints
   - mode="dataframe": normalize -> (optional) row sort -> assert_frame_equal

4) Date/time normalization (important for cross-engine comparisons):
   - DATE-like values are normalized to "YYYY-MM-DD"
   - datetime-like values at midnight are treated as date-only
   - other datetimes become "YYYY-MM-DD HH:MM:SS" (seconds precision, no tz)

Example
-------
    from runner import DualRunner
    import os

    PG_CONNINFO = (
        f"host=127.0.0.1 "
        f"port={os.getenv('POSTGRES_PORT', 5432)} "
        f"dbname={os.getenv('POSTGRES_DB')} "
        f"user={os.getenv('POSTGRES_USER')} "
        f"password={os.getenv('POSTGRES_PASSWORD')}"
    )

    runner = DualRunner(pg_conninfo=PG_CONNINFO, duckdb_path=":memory:")

    runner.check(\"\"\"
    --sql
    drop table if exists load_sample;
    create table load_sample (
        sample_date date primary key,
        load_value integer
    );
    insert into load_sample values
        ('2018-02-01', 1024),
        ('2018-02-02', 2366);
    select * from load_sample;
    \"\"\", mode="hash")
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Union, Literal
import hashlib
import re
import datetime

import pandas as pd
import numpy as np

import psycopg
import duckdb


# =============================================================================
# SQL preprocessing / splitting
# =============================================================================

_LINE_COMMENT_RE = re.compile(r"--.*?$", flags=re.M)
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", flags=re.S)


def strip_sql_comments(sql: str) -> str:
    """
    Strip SQL comments from a script.

    Parameters
    ----------
    sql:
        SQL text that may contain:
        - line comments:  -- comment
        - block comments: /* comment */

    Returns
    -------
    str
        SQL with comments removed.

    Notes
    -----
    This makes semicolon splitting more robust for Jupyter-style scripts that start
    with `--sql` and contain comments.
    """
    sql = _BLOCK_COMMENT_RE.sub("", sql)
    sql = _LINE_COMMENT_RE.sub("", sql)
    return sql


def split_sql_statements(sql: str) -> list[str]:
    """
    Split a multi-statement SQL script into individual statements.

    Parameters
    ----------
    sql:
        SQL script containing one or more statements separated by ';'.

    Returns
    -------
    list[str]
        Non-empty SQL statements in execution order.

    Limitations
    -----------
    This function does not fully parse SQL grammar. If you have semicolons inside
    string literals, consider using `sqlparse` for robust splitting.
    """
    cleaned = strip_sql_comments(sql)
    parts = [s.strip() for s in cleaned.strip().split(";")]
    return [p for p in parts if p]


# =============================================================================
# DataFrame normalization / hashing
# =============================================================================

# Use separators unlikely to appear in normal data to avoid concatenation ambiguity.
_COL_SEP = "\x1f"   # Unit Separator
_ROW_SEP = "\n"
_NULL = "<NULL>"


def normalize_df_shape(
    df: pd.DataFrame,
    *,
    ignore_col_order: bool = True,
) -> pd.DataFrame:
    """
    Normalize DataFrame shape for comparison.

    Parameters
    ----------
    df:
        Input DataFrame.
    ignore_col_order:
        If True, columns are sorted alphabetically to remove column-order differences.

    Returns
    -------
    pd.DataFrame
        DataFrame with stable column order and reset index.

    Notes
    -----
    We intentionally do NOT attempt dtype inference here (e.g., pd.to_datetime)
    to avoid noisy warnings and engine-specific parsing differences.
    """
    out = df.copy()
    if ignore_col_order:
        out = out.reindex(sorted(out.columns), axis=1)
    return out.reset_index(drop=True)


def sort_rows_stably(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sort rows using all columns as keys.

    Parameters
    ----------
    df:
        DataFrame to sort.

    Returns
    -------
    pd.DataFrame
        Sorted DataFrame (stable sort). If values are not mutually comparable,
        falls back to sorting by string-cast values.

    Why this exists
    ---------------
    When comparing results without ORDER BY, row order may differ across engines.
    Stable sorting helps compare the *set of rows*.
    """
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
    """
    Convert a single cell value into a stable textual representation.

    Parameters
    ----------
    x:
        Cell value from pandas DataFrame.
    float_sig:
        Significant digits for floats to avoid representation noise.

    Returns
    -------
    str
        Normalized string.

    Key rules
    ---------
    - Missing values -> "<NULL>"
    - DATE-like -> "YYYY-MM-DD"
    - Datetime-like:
        * if exactly midnight -> treat as date-only "YYYY-MM-DD"
        * else -> "YYYY-MM-DD HH:MM:SS" (seconds precision, no timezone)
    - Floats -> significant-digits formatting (default 10)
    """
    # Unify missing values (None, NaN, pandas NA, etc.)
    if x is None:
        return _NULL
    try:
        if pd.isna(x):
            return _NULL
    except Exception:
        pass

    # pandas Timestamp
    if isinstance(x, pd.Timestamp):
        ts = x
        # Remove timezone for stable cross-engine stringification
        if ts.tzinfo is not None:
            ts = ts.tz_convert(None)

        # If midnight, treat it as date-only (common for DATE columns)
        if (
            ts.hour == 0 and ts.minute == 0 and ts.second == 0
            and ts.microsecond == 0 and ts.nanosecond == 0
        ):
            return ts.date().isoformat()

        dt = ts.to_pydatetime().replace(tzinfo=None)
        return dt.isoformat(sep=" ", timespec="seconds")

    # numpy datetime64
    if isinstance(x, np.datetime64):
        ts = pd.to_datetime(x)
        if (
            ts.hour == 0 and ts.minute == 0 and ts.second == 0
            and ts.microsecond == 0 and ts.nanosecond == 0
        ):
            return ts.date().isoformat()
        dt = ts.to_pydatetime().replace(tzinfo=None)
        return dt.isoformat(sep=" ", timespec="seconds")

    # Python date (but not datetime)
    if isinstance(x, datetime.date) and not isinstance(x, datetime.datetime):
        return x.isoformat()

    # Python datetime
    if isinstance(x, datetime.datetime):
        dt = x
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)

        if dt.hour == 0 and dt.minute == 0 and dt.second == 0 and dt.microsecond == 0:
            return dt.date().isoformat()

        return dt.isoformat(sep=" ", timespec="seconds")

    # Floats: reduce false diffs from float representation
    if isinstance(x, (float, np.floating)):
        return format(float(x), f".{float_sig}g")

    # Fallback: string conversion
    return str(x)


def fingerprint_df(
    df: pd.DataFrame,
    *,
    ignore_row_order: bool = True,
    ignore_col_order: bool = True,
    algo: str = "sha256",
    float_sig: int = 10,
) -> str:
    """
    Compute a stable fingerprint for a DataFrame.

    Parameters
    ----------
    df:
        DataFrame to fingerprint.
    ignore_row_order:
        If True, treats the DataFrame as a multiset of rows (row order ignored).
    ignore_col_order:
        If True, sorts columns alphabetically before hashing.
    algo:
        Hash algorithm name (default: sha256). hashlib-supported names are allowed.
    float_sig:
        Significant digits for float normalization.

    Returns
    -------
    str
        Hex digest string.

    How it works
    ------------
    1) Fix column order (optional)
    2) Convert each row to a normalized string (safe separators)
    3) Sort row strings (optional)
    4) Hash the concatenated representation
    """
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
    """
    Run the same SQL against Postgres and DuckDB, then compare the last result set.

    Parameters
    ----------
    pg_conninfo:
        psycopg3 connection string.
        Accepts:
          - keyword style: "host=... port=... dbname=... user=... password=..."
          - URL style:     "postgresql://user:pass@host:port/dbname"
        (NOTE: SQLAlchemy URLs like "postgresql+psycopg://..." are NOT accepted.
               Remove the "+psycopg" part if you want URL style.)
    duckdb_path:
        DuckDB DB path; ":memory:" for in-memory.

    Behavior
    --------
    - Connections are created lazily and reused across calls (good for notebooks).
    - Each run commits at the end on Postgres.
    - The "last result-set statement" is compared (SELECT / RETURNING).
    """

    pg_conninfo: str
    duckdb_path: str = ":memory:"

    _pg: Optional[psycopg.Connection] = None
    _dd: Optional[duckdb.DuckDBPyConnection] = None

    # -------------
    # Connections
    # -------------

    def _get_pg(self) -> psycopg.Connection:
        """Create or reuse the Postgres connection."""
        if self._pg is None or self._pg.closed:
            self._pg = psycopg.connect(self.pg_conninfo)
        return self._pg

    def _get_dd(self) -> duckdb.DuckDBPyConnection:
        """Create or reuse the DuckDB connection."""
        if self._dd is None:
            self._dd = duckdb.connect(self.duckdb_path)
        return self._dd

    # -------------
    # Execution
    # -------------

    def run_pg(self, sql: str, params: Optional[Dict[str, Any]] = None) -> Result:
        """
        Execute SQL script on Postgres and return the last result set.

        Parameters
        ----------
        sql:
            Multi-statement SQL script.
        params:
            Optional parameters dict (passed to each statement).

        Returns
        -------
        Result
            - DataFrame: if a SELECT/RETURNING result set was produced (last one wins)
            - dict: metadata if no result set
        """
        params = params or {}
        conn = self._get_pg()

        last_df: Optional[pd.DataFrame] = None
        executed = 0

        with conn.cursor() as cur:
            for stmt in split_sql_statements(sql):
                executed += 1
                cur.execute(stmt, params)

                # In psycopg, result sets have cursor.description
                if cur.description is not None:
                    rows = cur.fetchall()
                    cols = [d.name for d in cur.description]
                    last_df = pd.DataFrame(rows, columns=cols)

        conn.commit()

        if last_df is not None:
            return last_df
        return {"ok": True, "executed": executed, "note": "no result set"}

    def run_dd(self, sql: str, params: Optional[Dict[str, Any]] = None) -> Result:
        """
        Execute SQL script on DuckDB and return the last result set.

        Parameters
        ----------
        sql:
            Multi-statement SQL script.
        params:
            Optional parameters dict (passed to each statement).

        Returns
        -------
        Result
            - DataFrame: if a result set was produced (last one wins)
            - dict: metadata if no result set
        """
        params = params or {}
        conn = self._get_dd()

        last_df: Optional[pd.DataFrame] = None
        executed = 0

        for stmt in split_sql_statements(sql):
            executed += 1
            res = conn.execute(stmt, params)

            # DuckDB: SELECT typically supports res.df()
            try:
                df = res.df()
                # DDL/DML may return empty df() with no columns -> ignore those
                if len(df.columns) > 0:
                    last_df = df
            except Exception:
                pass

        if last_df is not None:
            return last_df
        return {"ok": True, "executed": executed, "note": "no result set"}

    # -------------
    # Comparison
    # -------------

    def check(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        mode: CompareMode = "hash",
        ignore_row_order: bool = True,
        ignore_col_order: bool = True,
        float_sig: int = 10,
        verbose: bool = True,
        show_head: int = 10,
    ) -> Result:
        """
        Run SQL on both engines and compare the last result set.

        Parameters
        ----------
        sql:
            SQL script to execute.
        params:
            Optional parameters dictionary for both engines.
        mode:
            - "hash" (default): compare SHA-256 fingerprints (robust to dtype differences)
            - "dataframe": compare normalized DataFrames (useful for debugging)
        ignore_row_order:
            If True, ignore differences in row ordering.
        ignore_col_order:
            If True, ignore differences in column ordering.
        float_sig:
            Significant digits used when normalizing floats for hashing.
        verbose:
            Print "same" / "diff" and diagnostics.
        show_head:
            Number of rows to show for each engine when diff is detected.

        Returns
        -------
        Result
            Returns the Postgres output (DataFrame or metadata dict).

        Raises
        ------
        RuntimeError
            If either engine fails to execute the SQL. The printed diagnostics indicates which.
        """
        params = params or {}

        # Run both sides and capture errors separately to report which engine failed.
        pg_err: Optional[Exception] = None
        dd_err: Optional[Exception] = None

        try:
            pg_out = self.run_pg(sql, params=params)
        except Exception as e:
            pg_out = None
            pg_err = e

        try:
            dd_out = self.run_dd(sql, params=params)
        except Exception as e:
            dd_out = None
            dd_err = e

        if pg_err or dd_err:
            if verbose:
                if pg_err:
                    print("PG ERROR:")
                    print(pg_err)
                if dd_err:
                    print("DUCKDB ERROR:")
                    print(dd_err)
            raise RuntimeError(f"Execution failed (pg={bool(pg_err)}, duckdb={bool(dd_err)})")

        # If either side did not produce a DataFrame result set, we cannot compare.
        if not isinstance(pg_out, pd.DataFrame) or not isinstance(dd_out, pd.DataFrame):
            if verbose:
                print("no comparable result set (SELECT/RETURNING not found on one/both sides)")
            return pg_out

        # Normalize only shape/order here (no dtype inference to avoid warnings/noise).
        pg_df = normalize_df_shape(pg_out, ignore_col_order=ignore_col_order)
        dd_df = normalize_df_shape(dd_out, ignore_col_order=ignore_col_order)

        if mode == "hash":
            # Hash comparison: type differences are absorbed by _normalize_cell_for_text
            pg_fp = fingerprint_df(
                pg_df,
                ignore_row_order=ignore_row_order,
                ignore_col_order=False,  # already applied above
                algo="sha256",
                float_sig=float_sig,
            )
            dd_fp = fingerprint_df(
                dd_df,
                ignore_row_order=ignore_row_order,
                ignore_col_order=False,
                algo="sha256",
                float_sig=float_sig,
            )

            same = (pg_fp == dd_fp)

            if verbose:
                print("same" if same else "diff")
                if not same:
                    print("PG fingerprint:", pg_fp)
                    print("DuckDB fingerprint:", dd_fp)
                    print("PG dtypes:\n", pg_df.dtypes)
                    print("DuckDB dtypes:\n", dd_df.dtypes)
                    print("PG head:")
                    print(pg_df.head(show_head))
                    print("DuckDB head:")
                    print(dd_df.head(show_head))

            return pg_out

        # DataFrame comparison mode: helpful for debugging differences.
        if ignore_row_order:
            pg_cmp = sort_rows_stably(pg_df)
            dd_cmp = sort_rows_stably(dd_df)
        else:
            pg_cmp = pg_df.reset_index(drop=True)
            dd_cmp = dd_df.reset_index(drop=True)

        same = True
        try:
            pd.testing.assert_frame_equal(pg_cmp, dd_cmp, check_dtype=False)
        except AssertionError:
            same = False

        if verbose:
            print("same" if same else "diff")
            if not same:
                print("PG dtypes:\n", pg_cmp.dtypes)
                print("DuckDB dtypes:\n", dd_cmp.dtypes)
                print("PG head:")
                print(pg_cmp.head(show_head))
                print("DuckDB head:")
                print(dd_cmp.head(show_head))

        return pg_out

    # -------------
    # Cleanup
    # -------------

    def close(self) -> None:
        """
        Close both connections (optional cleanup).

        In notebooks you can often ignore this, but it's good practice to call it
        when you're done (especially if you create many runners).
        """
        if self._pg is not None and not self._pg.closed:
            try:
                self._pg.close()
            except Exception:
                pass
        self._pg = None

        if self._dd is not None:
            try:
                self._dd.close()
            except Exception:
                pass
        self._dd = None
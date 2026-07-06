import marimo

__generated_with = "0.11.0"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        """
        # SQL 練習ノート 01 — 基礎

        `init.py` で取り込んだ DuckDB のデータを使って SQL を練習します。
        データは **スキーマ** で分かれています（`data/<スキーマ>/<テーブル>.csv` に対応）。

        - `ecommerce` … `customers` / `products` / `orders` / `order_items` と、結合ビュー `order_details`
        - `hr` … `departments` / `employees`

        このノートは既定スキーマを `ecommerce` にしてあるので、`ecommerce` 内は
        非修飾（例: `customers`）で書けます。別スキーマは `hr.employees` のように
        スキーマ名を付けて参照します。
        """
    )
    return


@app.cell
def _():
    import duckdb
    import marimo as mo
    return duckdb, mo


@app.cell
def _(duckdb, mo):
    # ノートブック（learning/）の1つ上がプロジェクトルート
    db_path = mo.notebook_dir().parent / "db" / "learning.duckdb"
    conn = duckdb.connect(str(db_path), read_only=True)
    conn.execute("USE ecommerce;")  # 既定スキーマを ecommerce に設定
    return conn, db_path


@app.cell(hide_code=True)
def _(mo):
    mo.md("""## 1. まずは全件表示（SELECT）""")
    return


@app.cell
def _(conn, mo):
    _df = mo.sql(
        """
        SELECT *
        FROM customers;
        """,
        engine=conn,
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""## 2. 絞り込みと並べ替え（WHERE / ORDER BY）""")
    return


@app.cell
def _(conn, mo):
    _df = mo.sql(
        """
        SELECT name, city, signup_date
        FROM customers
        WHERE city = 'Tokyo'
        ORDER BY signup_date;
        """,
        engine=conn,
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""## 3. 集計（GROUP BY）""")
    return


@app.cell
def _(conn, mo):
    _df = mo.sql(
        """
        SELECT status, COUNT(*) AS order_count
        FROM orders
        GROUP BY status
        ORDER BY order_count DESC;
        """,
        engine=conn,
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""## 4. テーブルの結合（JOIN）""")
    return


@app.cell
def _(conn, mo):
    _df = mo.sql(
        """
        SELECT
            o.order_id,
            c.name AS customer_name,
            o.order_date,
            o.status
        FROM orders AS o
        JOIN customers AS c ON c.customer_id = o.customer_id
        ORDER BY o.order_date;
        """,
        engine=conn,
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        """
        ## 5. ビューを使った集計

        `init.sql` で定義した `order_details` ビュー（`ecommerce` スキーマ内）を使うと、
        毎回 JOIN を書かずに「カテゴリ別の売上」などを集計できます。
        """
    )
    return


@app.cell
def _(conn, mo):
    _df = mo.sql(
        """
        SELECT
            category,
            SUM(line_total) AS revenue,
            SUM(quantity)   AS units_sold
        FROM order_details
        WHERE status = 'completed'
        GROUP BY category
        ORDER BY revenue DESC;
        """,
        engine=conn,
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        """
        ## 6. スキーマをまたぐ

        既定スキーマ（`ecommerce`）以外のテーブルは、`hr.employees` のように
        `スキーマ名.テーブル名` で参照します。
        """
    )
    return


@app.cell
def _(conn, mo):
    _df = mo.sql(
        """
        SELECT
            d.department_name,
            COUNT(*)              AS n_employees,
            CAST(AVG(e.salary) AS BIGINT) AS avg_salary
        FROM hr.employees AS e
        JOIN hr.departments AS d ON d.department_id = e.department_id
        GROUP BY d.department_name
        ORDER BY n_employees DESC;
        """,
        engine=conn,
    )
    return


if __name__ == "__main__":
    app.run()

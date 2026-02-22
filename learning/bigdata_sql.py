import marimo

__generated_with = "0.19.9"
app = marimo.App()


@app.cell
def _():
    import os
    import pandas as pd
    import marimo as mo
    from runner import DualRunner
    from pathlib import Path
    from dotenv import load_dotenv


    env_path = Path("..") / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)

    # --- Pandas 設定 ---
    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_colwidth', None)

    # --- 接続情報の構築 ---
    pg_user = os.getenv("POSTGRES_USER", "postgres")
    pg_pass = os.getenv("POSTGRES_PASSWORD", "password")
    pg_host = os.getenv("POSTGRES_HOST", "127.0.0.1")
    pg_port = os.getenv("POSTGRES_PORT", "5432")
    pg_db   = os.getenv("POSTGRES_DB", "postgres")


    PG_CONNINFO = (
        f"host={pg_host} "
        f"port={pg_port} "
        f"dbname={pg_db} "
        f"user={pg_user} "
        f"password={pg_pass}"
    )

    # --- Runner の初期化 ---
    runner = DualRunner(
        pg_conninfo=PG_CONNINFO,
        duckdb_path=":memory:"
    )

    # --- 接続テスト表示 (ここが重要) ---
    # marimoでは display() ではなく、表示したい要素のリストを vstack に入れて返します
    pg_ver = runner.run_pg("select version()")
    dd_ver = runner.run_dd("select version()")

    mo.vstack([
        mo.md("## 🔌 Connection Check"),
        mo.ui.tabs({
            "🐘 PostgreSQL Version": pg_ver,
            "🦆 DuckDB Version": dd_ver
        })
    ])
    return mo, runner


@app.cell
def _(mo):
    mo.md(r"""
    # データ加工のためのSQL
    ## 一つの値に対する処理
    """)
    return


@app.cell
def _(runner):
    runner.check("""--sql
    drop table if exists access_log;
    create table access_log (
        stamp timestamp,
        referrer text,
        url text
    );
    insert into access_log (stamp, referrer, url) values
    ('2016-08-26 12:02:00', 'http://www.other.com/path1/index.php?k1=v1&k2=v2#Ref1', 'http://www.example.com/video/detail?id=001'),
    ('2016-08-26 12:02:01', 'http://www.other.net/path1/index.php?k1=v1&k2=v2#Ref1', 'http://www.example.com/video#ref'),
    ('2016-08-26 12:02:01', 'https://www.other.com/', 'http://www.example.com/book/detail?id=002');            
    select * from access_log;

    """)
    return


@app.cell
def _(mo, runner):
    mo.vstack([

    runner.pg("""--sql

    -- 正規表現を使って値を抽出する
    select
        stamp,
        referrer,
        url,
        substring(referrer from 'https?://([^/]*)') as referrer_domain,
        substring(url from '//[^/]+([^?#]+)') as path,
        substring(url from 'id=([^&]*)') as id
    from access_log
    """),

    runner.dd("""--sql
    select
        stamp,
        referrer,
        url,
        regexp_extract(referrer, 'https?://([^/]*)', 1) as referrer_domain,
        regexp_extract(url,  '//[^/]+([^?#]+)', 1) as path,
        regexp_extract(url,  'id=([^&]*)', 1) as id
    from access_log

    """)

    ])


    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 文字列を配列に分解する

    `split_part(str, '/', 2)` などと書けば、分割する文字と分割した後にインデックスを指定して抽出できる。duckdb でも同じ関数。
    """)
    return


@app.cell
def _(mo, runner):

    mo.vstack([
    runner.pg("""--sql
    -- ulr のパスをスラッシュで分割して階層を抽出する
    select
        stamp,
        url,
        split_part(substring(url from '//[^/]+([^?#]+)'), '/', 2) as path_1,
        split_part(substring(url from '//[^/]+([^?#]+)'), '/', 3) as path_2
    from access_log
    """),

    runner.dd("""--sql
    -- ulr のパスをスラッシュで分割して階層を抽出する
    select
        stamp,
        url,
        split_part(regexp_extract(url, '//[^/]+([^?#]+)', 1), '/', 2) as path_1,
        split_part(regexp_extract(url, '//[^/]+([^?#]+)', 1), '/', 3) as path_2
    from access_log
    """)

    ])
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 日付やタイムスタンプを扱う
    """)
    return


@app.cell
def _(runner):
    runner.check("""--sql
    select
        current_date as today,

        -- これはTZ付きデータになる
        current_timestamp as now_with_tz,

        -- localtimestamp や TZを指定すると、TZ無しデータになる
        localtimestamp as local_now,
        current_timestamp at time zone 'UTC' as now_utc,
        current_timestamp at time zone 'Asia/Tokyo' as now_tokyo,

        -- current_timestamp の代わりに now() を使っても同じ
        now() as now_with_tz_2,
        now() at time zone 'UTC' as now_utc_2,
        now() at time zone 'Asia/Tokyo' as now_tokyo_2
    """)
    return


@app.cell
def _(runner):
    runner.check("""--sql
    select
        '2016-08-26 12:02:00+09'::timestamptz as ts_with_tz,
        '2016-08-26 12:02:00'::timestamp as ts_without_tz,
        '2016-08-26'::date as only_date,

        -- cast で変換することも可能
        cast('2016-08-26 12:02:00+09' as timestamptz) as ts_with_tz_cast,
        cast('2016-08-26 12:02:00' as timestamp) as ts_without_tz_cast,
        cast('2016-08-26' as date) as only_date_cast,

        -- 以下の書き方もできる
        timestamptz '2016-08-26 12:02:00+09' as ts_with_tz_literal,
        timestamp '2016-08-26 12:02:00' as ts_without_tz_literal,
        date '2016-08-26' as only_date_literal
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### 日付・時刻から特定のフィールドを取り出す
    """)
    return


@app.cell
def _(runner):
    runner.check("""--sql
    with t as (
        select 
            '2016-08-26 12:02:39'::timestamp as stamp,
            '2016-08-26 12:02:39.82943'::timestamp as stamp_ms
    )

    select
        stamp,
        stamp_ms,
        extract(year from stamp) as year,
        extract(month from stamp) as month,
        extract(day from stamp) as day,
        extract(hour from stamp) as hour,
        extract(minute from stamp) as minute,

        -- second のあつかいが PG と duckdb で異なる
        -- second は duckb では小数点以下を切り捨てるが、PG では小数点以下も含む
        extract(second from stamp) as second, 
        extract(second from stamp_ms) as second_ms,

        extract(microsecond from stamp_ms) as microsecond 
    from t
             
             
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### 欠損値をデフォルト値に置き換える
    """)
    return


@app.cell
def _(runner):
    runner.check("""--sql 
    drop table if exists purchase_log_with_coupon;
    create table purchase_log_with_coupon (
        purchase_id integer,
        amount integer,
        coupon integer
    );
    insert into purchase_log_with_coupon (purchase_id, amount, coupon) values
    (10001, 3280, null),
    (10002, 4650, 500),
    (10003, 3870, null);
    select * from purchase_log_with_coupon;
             
    """)
    return


@app.cell
def _(runner):
    #* 購入額から割引クーポンを引いて、実際の支払額を計算する
    runner.check("""--sql
    select
        purchase_id,
        amount,
        coupon,
        amount - coupon as actual_payment_pg, --null を四則演算すると null になるので注意
        amount - coalesce(coupon, 0) as actual_payment -- colalesce で null を 0 に変換してから計算する
    from purchase_log_with_coupon
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 複数の値に対する操作

    ### 文字列の連結
    """)
    return


@app.cell
def _(runner):
    runner.check("""--sql

    drop table if exists mst_user_location;
    create table mst_user_location (
        user_id varchar(10),
        pref_name varchar(50),
        city_name varchar(50)
    );
    insert into mst_user_location (user_id, pref_name, city_name) values
    ('U001', '東京都', '千代田区'),
    ('U002', '東京都', '渋谷区'),
    ('U003', '千葉県', '八千代市');
    select * from mst_user_location;

    """)

    return


@app.cell
def _(runner):
    runner.check("""--sql
             
    -- 都道府県と市区町村を結合してフル住所を作成する
    -- concat もしくは || 演算子を使う
    select
        concat(pref_name, city_name) as full_address,
        pref_name || city_name as full_address_2
    from mst_user_location
    """)
    return


@app.cell
def _(runner):
    runner.check("""--sql
    drop table if exists quarterly_sales;
    create table quarterly_sales (
        year integer,
        q1 integer,
        q2 integer,
        q3 integer,
        q4 integer
    );
    insert into quarterly_sales (year, q1, q2, q3, q4) values
    (2015, 82000, 83000, 78000, 83000),
    (2016, 85000, 85000, 80000, 81000),
    (2017, 92000, 81000, null, null);
    select * from quarterly_sales;
    """)
    return


@app.cell
def _(runner):
    runner.check("""--sql

    select
        year,
        q1, q2, q3, q4,

        -- 場合分け
        case
            when q1 < q2 then '+'
            when q1 = q2 then ' '
            when q1 > q2 then '-'
        end as judge,

        q2 - q1 as diff,

        -- sign(x)は x が正なら 1、負なら -1、0なら 0 を返す 
        sign(q2 - q1) as sign,

        -- 複数カラムの値の最大最小
        greatest(q1, q2, q3, q4) as greatest,
        least(q1, q2, q3, q4) as least,
             
        -- 平均は専用の関数はないので手動で数式をつくって計算
        -- DB によって表示桁数の違いがあるので注意
        -- null があると四則演算しても null
        (q1 + q2 + q3 + q4) / 4.0 as avg,

        -- nullを除いて 平均を計算するには
        -- 分子は coalesce で null を 0 に変換 しながら、
        --分母は null -> 0 に変換した上で sign() で 0 or 1 に変換して合計する
        (coalesce(q1,0) + coalesce(q2,0) + coalesce(q3,0) + coalesce(q4,0)) /
        (
            sign(coalesce(q1,0)) + sign(coalesce(q2,0)) +
            sign(coalesce(q3,0)) + sign(coalesce(q4,0))
        ) as avg_ignore_null

    from quarterly_sales
    order by year
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    **一般に複数のカラムを使った計算は面倒になるので、縦持ちに変換した後に集計したほうが良い**
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 2つの値の比率を計算する
    """)
    return


@app.cell
def _(runner):
    runner.check("""--sql 

    drop table if exists advertising_stats;
    create table advertising_stats (
        dt date,
        ad_id varchar(10),
        impressions integer,
        clicks integer
    );
    insert into advertising_stats (dt, ad_id, impressions, clicks) values
    ('2017-04-01', '001', 100000, 3000),
    ('2017-04-01', '002', 120000, 1200),
    ('2017-04-01', '003', 500000, 10000),
    ('2017-04-02', '001', 0, 0),
    ('2017-04-02', '002', 130000, 1400),
    ('2017-04-02', '003', 620000, 15000);
    select * from advertising_stats;
    """)
    return


@app.cell
def _(runner):
    runner.check("""--sql 
             
    -- click through rate (CTR) を計算する
    select
        dt,
        ad_id,
        -- clicks / impressions as ctr -- データに0が含まれるのでエラーになる
        -- そのため nullif(x, 0) を使って 0 の場合は null に変換してから計算する
        clicks::numeric / nullif(impressions, 0)::numeric as ctr_numeric,
        clicks::double precision / nullif(impressions, 0)::double precision  as ctr_double, 
        clicks::decimal / nullif(impressions, 0)::decimal  as ctr_decimal,
        (clicks*1.0) / (nullif(impressions, 0)*1.0)  as ctr_1,
        clicks::float / nullif(impressions, 0)::float  as ctr_float  -- これが両方で一番使いやすいか


    from advertising_stats




    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        select
            *
        from adventuers_log
        where
            event_date between '2023-01-01' and '2023-01-31'
            and event_type = 'battle'
            and damage >= 1000
        """
    )
    return


if __name__ == "__main__":
    app.run()

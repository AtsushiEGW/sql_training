import duckdb
import pandas as pd


# クエリ関数の作成
def sql(sentence: str) -> pd.DataFrame:
    with duckdb.connect('../preprocess_knock.duckdb') as con:
        df = con.execute(sentence).fetch_df()
        return df

# データの準備
sql("create or replace table category as select * from read_csv_auto('./work/data/category.csv');")
sql("create or replace table customer as select * from read_csv_auto('./work/data/customer.csv');")
sql("create or replace table geocode as select * from read_csv_auto('./work/data/geocode.csv');")
sql("create or replace table product as select * from read_csv_auto('./work/data/product.csv');")
sql("create or replace table receipt as select * from read_csv_auto('./work/data/receipt.csv');")
sql("create or replace table store as select * from read_csv_auto('./work/data/store.csv');")

print('data setup done!')
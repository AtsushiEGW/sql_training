import pandas as pd
from sqlalchemy import create_engine
from pathlib import Path

# データディレクトリのパスを path オブジェクトで指定
DATA_DIR = Path(__file__).parent / "work" / "data"

def connect_to_db():
    """Establish a connection to the PostgreSQL database using SQLAlchemy."""
    try:
        engine = create_engine("postgresql+psycopg2://postgres:postgres@localhost:5432/postgres")
        connection = engine.connect()
        print("Connection to the database established successfully.")
        return engine, connection
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        raise

def close_connection(connection):
    """Close the database connection."""
    if connection:
        connection.close()
        print("Database connection closed.")

def import_csv_files_to_postgres(engine):
    """Import all CSV files from work/data into PostgreSQL."""
    csv_files = list(DATA_DIR.glob('*.csv'))
    if not csv_files:
        print("No CSV files found in work/data/")
        return

    for csv_file in csv_files:
        table_name = csv_file.stem  # 拡張子なしファイル名
        print(f"Importing {csv_file.name} as table '{table_name}'...")
        df = pd.read_csv(csv_file)
        df.to_sql(table_name, engine, if_exists='replace', index=False)
        print(f"Table '{table_name}' imported successfully.")

def main():
    engine, connection = None, None
    try:
        engine, connection = connect_to_db()
        import_csv_files_to_postgres(engine)
    finally:
        if connection:
            close_connection(connection)

if __name__ == "__main__":
    main()
import marimo

__generated_with = "0.23.14"
app = marimo.App()


@app.cell
def _():
    import marimo as mo

    print("Hello, World!")

    return (mo,)


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        create or replace table fruits (
            pk_num, integer,
            name varchar(16),
            constraint pk_fruits primary key (pk_num)
        );
        insert into fruits values 
            ('Orange'),
            ('Orange'),
            ('Apple'),
            ('Apple'),
            ('Apple'),
            ('Grape');

        select * from fruits;

        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- IDを付与する
        -- シーケンスを作成する





        """
    )
    return


if __name__ == "__main__":
    app.run()

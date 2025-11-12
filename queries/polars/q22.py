import polars as pl

from queries.polars import utils

Q_NUM = 22


def q() -> None:
    customer = utils.get_customer_ds()
    orders = utils.get_orders_ds()

    var1 = "13"
    var2 = "31"
    var3 = "23"
    var4 = "29"
    var5 = "30"
    var6 = "18"
    var7 = "17"

    country_codes = [var1, var2, var3, var4, var5, var6, var7]

    # Calcula média de c_acctbal para países específicos com c_acctbal > 0
    avg_acctbal = (
        customer.filter(pl.col("c_phone").str.slice(0, 2).is_in(country_codes))
        .filter(pl.col("c_acctbal") > 0.00)
        .select(pl.mean("c_acctbal"))
        .collect()
        .item()
    )

    # Clientes sem ordens
    customers_with_orders = orders.select("o_custkey").unique()

    q_final = (
        customer.filter(pl.col("c_phone").str.slice(0, 2).is_in(country_codes))
        .filter(pl.col("c_acctbal") > avg_acctbal)
        .join(
            customers_with_orders,
            left_on="c_custkey",
            right_on="o_custkey",
            how="anti",
        )
        .with_columns(pl.col("c_phone").str.slice(0, 2).alias("cntrycode"))
        .group_by("cntrycode")
        .agg(
            pl.len().alias("numcust"),
            pl.sum("c_acctbal").alias("totacctbal"),
        )
        .sort(by="cntrycode")
    )

    utils.run_query(Q_NUM, q_final)


if __name__ == "__main__":
    q()


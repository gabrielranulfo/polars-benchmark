import polars as pl

from queries.polars import utils

Q_NUM = 13


def q() -> None:
    customer = utils.get_customer_ds()
    orders = utils.get_orders_ds()

    var1 = "special"
    var2 = "requests"

    # Left join com filtro na condição de join
    # O filtro está na condição do join, então filtramos orders antes do join
    orders_filtered = orders.filter(
        ~pl.col("o_comment").str.contains(f"{var1}{var2}")
    )
    
    c_orders = (
        customer.join(
            orders_filtered,
            left_on="c_custkey",
            right_on="o_custkey",
            how="left",
        )
        .group_by("c_custkey")
        .agg(pl.count("o_orderkey").alias("c_count"))
    )

    q_final = (
        c_orders.group_by("c_count")
        .agg(pl.len().alias("custdist"))
        .sort(by=["custdist", "c_count"], descending=[True, True])
    )

    utils.run_query(Q_NUM, q_final)


if __name__ == "__main__":
    q()


from datetime import date, timedelta

import polars as pl

from queries.polars import utils

Q_NUM = 12


def q() -> None:
    orders = utils.get_orders_ds()
    lineitem = utils.get_line_item_ds()

    var1 = "MAIL"
    var2 = "SHIP"
    var3 = date(1994, 1, 1)
    var4 = var3 + timedelta(days=365)  # +1 year

    q_final = (
        orders.join(lineitem, left_on="o_orderkey", right_on="l_orderkey")
        .filter(pl.col("l_shipmode").is_in([var1, var2]))
        .filter(pl.col("l_commitdate") < pl.col("l_receiptdate"))
        .filter(pl.col("l_shipdate") < pl.col("l_commitdate"))
        .filter(pl.col("l_receiptdate").is_between(var3, var4, closed="left"))
        .group_by("l_shipmode")
        .agg(
            pl.when(
                (pl.col("o_orderpriority") == "1-URGENT")
                | (pl.col("o_orderpriority") == "2-HIGH")
            )
            .then(1)
            .otherwise(0)
            .sum()
            .alias("high_line_count"),
            pl.when(
                (pl.col("o_orderpriority") != "1-URGENT")
                & (pl.col("o_orderpriority") != "2-HIGH")
            )
            .then(1)
            .otherwise(0)
            .sum()
            .alias("low_line_count"),
        )
        .sort(by="l_shipmode")
    )

    utils.run_query(Q_NUM, q_final)


if __name__ == "__main__":
    q()


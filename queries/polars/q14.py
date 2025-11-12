from datetime import date, timedelta

import polars as pl

from queries.polars import utils

Q_NUM = 14


def q() -> None:
    lineitem = utils.get_line_item_ds()
    part = utils.get_part_ds()

    var1 = date(1995, 9, 1)
    var2 = var1 + timedelta(days=30)  # +1 month

    q_final = (
        lineitem.join(part, left_on="l_partkey", right_on="p_partkey")
        .filter(pl.col("l_shipdate").is_between(var1, var2, closed="left"))
        .with_columns(
            (pl.col("l_extendedprice") * (1 - pl.col("l_discount"))).alias("disc_price")
        )
        .select(
            (
                100.00
                * pl.when(pl.col("p_type").str.starts_with("PROMO"))
                .then(pl.col("disc_price"))
                .otherwise(0)
                .sum()
                / pl.col("disc_price").sum()
            ).alias("promo_revenue")
        )
    )

    utils.run_query(Q_NUM, q_final)


if __name__ == "__main__":
    q()


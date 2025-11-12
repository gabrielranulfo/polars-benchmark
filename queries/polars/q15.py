from datetime import date, timedelta

import polars as pl

from queries.polars import utils

Q_NUM = 15


def q() -> None:
    lineitem = utils.get_line_item_ds()
    supplier = utils.get_supplier_ds()

    var1 = date(1996, 1, 1)
    var2 = var1 + timedelta(days=90)  # +3 months

    # Cria a "view" revenue como uma query intermediária
    revenue = (
        lineitem.filter(pl.col("l_shipdate").is_between(var1, var2, closed="left"))
        .with_columns(
            (pl.col("l_extendedprice") * (1 - pl.col("l_discount"))).alias("total_revenue")
        )
        .group_by("l_suppkey")
        .agg(pl.sum("total_revenue"))
        .select(
            pl.col("l_suppkey").alias("supplier_no"),
            pl.col("total_revenue"),
        )
    )

    max_revenue = revenue.select(pl.max("total_revenue")).collect().item()

    q_final = (
        supplier.join(revenue, left_on="s_suppkey", right_on="supplier_no")
        .filter(pl.col("total_revenue") == max_revenue)
        .select(
            "s_suppkey",
            "s_name",
            "s_address",
            "s_phone",
            "total_revenue",
        )
        .sort(by="s_suppkey")
    )

    utils.run_query(Q_NUM, q_final)


if __name__ == "__main__":
    q()


from datetime import date, timedelta

import polars as pl

from queries.polars import utils

Q_NUM = 20


def q() -> None:
    supplier = utils.get_supplier_ds()
    nation = utils.get_nation_ds()
    partsupp = utils.get_part_supp_ds()
    part = utils.get_part_ds()
    lineitem = utils.get_line_item_ds()

    var1 = "forest"
    var2 = date(1994, 1, 1)
    var3 = var2 + timedelta(days=365)  # +1 year
    var4 = "CANADA"

    # Partes que começam com var1
    matching_parts = part.filter(pl.col("p_name").str.starts_with(var1)).select("p_partkey")

    # Calcula 0.5 * sum(l_quantity) por partkey e suppkey
    lineitem_agg = (
        lineitem.filter(pl.col("l_shipdate").is_between(var2, var3, closed="left"))
        .group_by("l_partkey", "l_suppkey")
        .agg((0.5 * pl.sum("l_quantity")).alias("half_qty"))
    )

    # Partsupp com availqty > half_qty
    qualifying_partsupp = (
        partsupp.join(matching_parts, left_on="ps_partkey", right_on="p_partkey", how="semi")
        .join(
            lineitem_agg,
            left_on=["ps_partkey", "ps_suppkey"],
            right_on=["l_partkey", "l_suppkey"],
        )
        .filter(pl.col("ps_availqty") > pl.col("half_qty"))
        .select("ps_suppkey")
    )

    q_final = (
        supplier.join(qualifying_partsupp, left_on="s_suppkey", right_on="ps_suppkey", how="semi")
        .join(nation, left_on="s_nationkey", right_on="n_nationkey")
        .filter(pl.col("n_name") == var4)
        .select("s_name", "s_address")
        .sort(by="s_name")
    )

    utils.run_query(Q_NUM, q_final)


if __name__ == "__main__":
    q()


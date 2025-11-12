import polars as pl

from queries.polars import utils

Q_NUM = 17


def q() -> None:
    lineitem = utils.get_line_item_ds()
    part = utils.get_part_ds()

    var1 = "Brand#23"
    var2 = "MED CASE"

    # Calcula a média de quantidade por partkey
    avg_qty = (
        lineitem.group_by("l_partkey")
        .agg(pl.mean("l_quantity").alias("avg_qty"))
    )

    q_final = (
        part.filter(pl.col("p_brand") == var1)
        .filter(pl.col("p_container") == var2)
        .join(lineitem, left_on="p_partkey", right_on="l_partkey")
        .join(avg_qty, left_on="p_partkey", right_on="l_partkey")
        .filter(pl.col("l_quantity") < 0.2 * pl.col("avg_qty"))
        .select((pl.sum("l_extendedprice") / 7.0).alias("avg_yearly"))
    )

    utils.run_query(Q_NUM, q_final)


if __name__ == "__main__":
    q()


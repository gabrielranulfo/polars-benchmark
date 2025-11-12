import polars as pl

from queries.polars import utils

Q_NUM = 19


def q() -> None:
    lineitem = utils.get_line_item_ds()
    part = utils.get_part_ds()

    var1 = "Brand#12"
    var4 = 1
    var2 = "Brand#23"
    var5 = 10
    var3 = "Brand#34"
    var6 = 20

    q_final = (
        lineitem.join(part, left_on="l_partkey", right_on="p_partkey")
        .filter(
            (
                (pl.col("p_brand") == var1)
                & (pl.col("p_container").is_in(["SM CASE", "SM BOX", "SM PACK", "SM PKG"]))
                & (pl.col("l_quantity").is_between(var4, var4 + 10, closed="both"))
                & (pl.col("p_size").is_between(1, 5, closed="both"))
                & (pl.col("l_shipmode").is_in(["AIR", "AIR REG"]))
                & (pl.col("l_shipinstruct") == "DELIVER IN PERSON")
            )
            | (
                (pl.col("p_brand") == var2)
                & (pl.col("p_container").is_in(["MED BAG", "MED BOX", "MED PKG", "MED PACK"]))
                & (pl.col("l_quantity").is_between(var5, var5 + 10, closed="both"))
                & (pl.col("p_size").is_between(1, 10, closed="both"))
                & (pl.col("l_shipmode").is_in(["AIR", "AIR REG"]))
                & (pl.col("l_shipinstruct") == "DELIVER IN PERSON")
            )
            | (
                (pl.col("p_brand") == var3)
                & (pl.col("p_container").is_in(["LG CASE", "LG BOX", "LG PACK", "LG PKG"]))
                & (pl.col("l_quantity").is_between(var6, var6 + 10, closed="both"))
                & (pl.col("p_size").is_between(1, 15, closed="both"))
                & (pl.col("l_shipmode").is_in(["AIR", "AIR REG"]))
                & (pl.col("l_shipinstruct") == "DELIVER IN PERSON")
            )
        )
        .with_columns(
            (pl.col("l_extendedprice") * (1 - pl.col("l_discount"))).alias("revenue")
        )
        .select(pl.sum("revenue"))
    )

    utils.run_query(Q_NUM, q_final)


if __name__ == "__main__":
    q()


from datetime import date

import polars as pl

from queries.polars import utils

Q_NUM = 8


def q() -> None:
    part = utils.get_part_ds()
    supplier = utils.get_supplier_ds()
    lineitem = utils.get_line_item_ds()
    orders = utils.get_orders_ds()
    customer = utils.get_customer_ds()
    nation = utils.get_nation_ds()
    region = utils.get_region_ds()

    var1 = "BRAZIL"  # :1 - nação do fornecedor
    var2 = "AMERICA"  # :2 - região
    var3 = "ECONOMY ANODIZED STEEL"  # :3 - tipo de peça
    var4 = date(1995, 1, 1)
    var5 = date(1996, 12, 31)

    # Filtra a região
    region_filtered = region.filter(pl.col("r_name") == var2)

    # Filtra a nação do fornecedor
    n2 = nation.filter(pl.col("n_name") == var1)

    # Filtra o tipo de peça
    part_filtered = part.filter(pl.col("p_type") == var3)

    # Faz os joins conforme a query SQL
    all_nations = (
        part_filtered.join(lineitem, left_on="p_partkey", right_on="l_partkey")
        .join(supplier, left_on="l_suppkey", right_on="s_suppkey")
        .join(orders, left_on="l_orderkey", right_on="o_orderkey")
        .join(customer, left_on="o_custkey", right_on="c_custkey")
        .join(nation, left_on="c_nationkey", right_on="n_nationkey")
        .rename({"n_name": "cust_nation"})
        .join(region_filtered, left_on="n_regionkey", right_on="r_regionkey")
        .join(n2, left_on="s_nationkey", right_on="n_nationkey")
        .rename({"n_name": "supp_nation"})
        .filter(pl.col("o_orderdate").is_between(var4, var5))
        .with_columns(
            pl.col("o_orderdate").dt.year().alias("o_year"),
            (pl.col("l_extendedprice") * (1 - pl.col("l_discount"))).alias("volume"),
        )
    )

    q_final = (
        all_nations.group_by("o_year")
        .agg(
            (
                pl.when(pl.col("supp_nation") == var1).then(pl.col("volume")).otherwise(0).sum()
                / pl.col("volume").sum()
            ).alias("mkt_share")
        )
        .sort(by="o_year")
    )

    utils.run_query(Q_NUM, q_final)


if __name__ == "__main__":
    q()
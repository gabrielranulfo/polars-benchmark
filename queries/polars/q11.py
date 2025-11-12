import polars as pl

from queries.polars import utils

Q_NUM = 11


def q() -> None:
    partsupp = utils.get_part_supp_ds()
    supplier = utils.get_supplier_ds()
    nation = utils.get_nation_ds()

    var1 = "GERMANY"
    var2 = 0.0001

    # Primeiro calcula o valor total para a nação
    total_value = (
        partsupp.join(supplier, left_on="ps_suppkey", right_on="s_suppkey")
        .join(nation, left_on="s_nationkey", right_on="n_nationkey")
        .filter(pl.col("n_name") == var1)
        .with_columns((pl.col("ps_supplycost") * pl.col("ps_availqty")).alias("value"))
        .select(pl.sum("value"))
        .collect()
        .item()
    )

    threshold = total_value * var2

    q_final = (
        partsupp.join(supplier, left_on="ps_suppkey", right_on="s_suppkey")
        .join(nation, left_on="s_nationkey", right_on="n_nationkey")
        .filter(pl.col("n_name") == var1)
        .with_columns((pl.col("ps_supplycost") * pl.col("ps_availqty")).alias("value"))
        .group_by("ps_partkey")
        .agg(pl.sum("value"))
        .filter(pl.col("value") > threshold)
        .sort(by="value", descending=True)
    )

    utils.run_query(Q_NUM, q_final)


if __name__ == "__main__":
    q()


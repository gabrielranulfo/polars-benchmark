import polars as pl

from queries.polars import utils

Q_NUM = 21


def q() -> None:
    supplier = utils.get_supplier_ds()
    lineitem = utils.get_line_item_ds()
    orders = utils.get_orders_ds()
    nation = utils.get_nation_ds()

    var1 = "SAUDI ARABIA"

    # Linhas base com receiptdate > commitdate
    l1 = lineitem.filter(
        pl.col("l_receiptdate") > pl.col("l_commitdate")
    )

    # EXISTS: existe outra linha no mesmo orderkey com suppkey diferente
    # Verifica se há múltiplos suppkeys diferentes no mesmo orderkey
    orders_with_other_suppliers = (
        lineitem.group_by("l_orderkey")
        .agg(pl.n_unique("l_suppkey").alias("supplier_count"))
        .filter(pl.col("supplier_count") > 1)
        .select("l_orderkey")
    )

    # NOT EXISTS: não existe outra linha no mesmo orderkey com suppkey diferente
    # E que também tenha receiptdate > commitdate
    # Cria uma lista de suppkeys únicos que estão atrasados no mesmo orderkey
    other_late_suppliers = (
        lineitem.filter(pl.col("l_receiptdate") > pl.col("l_commitdate"))
        .group_by("l_orderkey")
        .agg(pl.col("l_suppkey").unique().alias("late_suppkeys"))
    )

    q_final = (
        supplier.join(l1, left_on="s_suppkey", right_on="l_suppkey")
        .join(orders, left_on="l_orderkey", right_on="o_orderkey")
        .filter(pl.col("o_orderstatus") == "F")
        .join(orders_with_other_suppliers, left_on="l_orderkey", right_on="l_orderkey", how="semi")
        .join(nation, left_on="s_nationkey", right_on="n_nationkey")
        .filter(pl.col("n_name") == var1)
        .join(
            other_late_suppliers,
            left_on="l_orderkey",
            right_on="l_orderkey",
            how="left",
        )
        .filter(
            (pl.col("late_suppkeys").is_null())
            | (
                # Verifica se há apenas um suppkey único e é igual ao atual
                # (ou seja, não há outras linhas atrasadas com suppkey diferente)
                (pl.col("late_suppkeys").list.len() == 1)
                & (pl.col("late_suppkeys").list.first() == pl.col("s_suppkey"))
            )
        )
        .group_by("s_name")
        .agg(pl.len().alias("numwait"))
        .sort(by=["numwait", "s_name"], descending=[True, False])
        .head(100)
    )

    utils.run_query(Q_NUM, q_final)


if __name__ == "__main__":
    q()


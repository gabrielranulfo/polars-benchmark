import polars as pl

from queries.polars import utils

Q_NUM = 16


def q() -> None:
    partsupp = utils.get_part_supp_ds()
    part = utils.get_part_ds()
    supplier = utils.get_supplier_ds()

    var1 = "Brand#45"
    var2 = "MEDIUM POLISHED"
    var3 = 49
    var4 = 14
    var5 = 23
    var6 = 45
    var7 = 19
    var8 = 3
    var9 = 36
    var10 = 9

    # Fornecedores a excluir
    excluded_suppliers = (
        supplier.filter(pl.col("s_comment").str.contains("Customer%Complaints"))
        .select("s_suppkey")
    )

    q_final = (
        part.join(partsupp, left_on="p_partkey", right_on="ps_partkey")
        .filter(pl.col("p_brand") != var1)
        .filter(~pl.col("p_type").str.starts_with(var2))
        .filter(
            pl.col("p_size").is_in([var3, var4, var5, var6, var7, var8, var9, var10])
        )
        .join(
            excluded_suppliers,
            left_on="ps_suppkey",
            right_on="s_suppkey",
            how="anti",
        )
        .group_by("p_brand", "p_type", "p_size")
        .agg(pl.n_unique("ps_suppkey").alias("supplier_cnt"))
        .sort(
            by=["supplier_cnt", "p_brand", "p_type", "p_size"],
            descending=[True, False, False, False],
        )
    )

    utils.run_query(Q_NUM, q_final)


if __name__ == "__main__":
    q()


from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from queries.pandas import utils

if TYPE_CHECKING:
    pass

Q_NUM = 16


def q() -> None:
    part_supp_ds = utils.get_part_supp_ds
    part_ds = utils.get_part_ds
    supplier_ds = utils.get_supplier_ds

    # first call one time to cache in case we don't include the IO times
    part_supp_ds()
    part_ds()
    supplier_ds()

    def query() -> pd.DataFrame:
        nonlocal part_supp_ds
        nonlocal part_ds
        nonlocal supplier_ds
        part_supp_ds = part_supp_ds()
        part_ds = part_ds()
        supplier_ds = supplier_ds()

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
        excluded_suppliers = supplier_ds[
            supplier_ds["s_comment"].str.contains("Customer%Complaints", na=False)
        ]["s_suppkey"]

        jn = part_ds.merge(
            part_supp_ds, left_on="p_partkey", right_on="ps_partkey"
        )

        filt = jn[
            (jn["p_brand"] != var1)
            & (~jn["p_type"].str.startswith(var2, na=False))
            & (jn["p_size"].isin([var3, var4, var5, var6, var7, var8, var9, var10]))
            & (~jn["ps_suppkey"].isin(excluded_suppliers))
        ]

        gb = filt.groupby(["p_brand", "p_type", "p_size"], as_index=False)
        agg = gb.agg(
            supplier_cnt=pd.NamedAgg(column="ps_suppkey", aggfunc="nunique")
        )

        result_df = agg.sort_values(
            by=["supplier_cnt", "p_brand", "p_type", "p_size"],
            ascending=[False, True, True, True],
        )

        return result_df  # type: ignore[no-any-return]

    utils.run_query(Q_NUM, query)


if __name__ == "__main__":
    q()



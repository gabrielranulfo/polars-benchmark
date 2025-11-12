from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from queries.pandas import utils

if TYPE_CHECKING:
    pass

Q_NUM = 21


def q() -> None:
    supplier_ds = utils.get_supplier_ds
    line_item_ds = utils.get_line_item_ds
    orders_ds = utils.get_orders_ds
    nation_ds = utils.get_nation_ds

    # first call one time to cache in case we don't include the IO times
    supplier_ds()
    line_item_ds()
    orders_ds()
    nation_ds()

    def query() -> pd.DataFrame:
        nonlocal supplier_ds
        nonlocal line_item_ds
        nonlocal orders_ds
        nonlocal nation_ds
        supplier_ds = supplier_ds()
        line_item_ds = line_item_ds()
        orders_ds = orders_ds()
        nation_ds = nation_ds()

        var1 = "SAUDI ARABIA"

        # Linhas base com receiptdate > commitdate
        l1 = line_item_ds[line_item_ds["l_receiptdate"] > line_item_ds["l_commitdate"]]

        # EXISTS: existe outra linha no mesmo orderkey com suppkey diferente
        orders_with_other_suppliers = line_item_ds.groupby("l_orderkey", as_index=False).agg(
            supplier_count=pd.NamedAgg(column="l_suppkey", aggfunc="nunique")
        )
        orders_with_other_suppliers = orders_with_other_suppliers[
            orders_with_other_suppliers["supplier_count"] > 1
        ]["l_orderkey"]

        # NOT EXISTS: não existe outra linha no mesmo orderkey com suppkey diferente
        # E que também tenha receiptdate > commitdate
        # Usa nunique para verificar se há apenas um suppkey único
        other_late_suppliers = l1.groupby("l_orderkey", as_index=False).agg(
            late_suppkey_count=pd.NamedAgg(column="l_suppkey", aggfunc="nunique"),
            late_suppkey_unique=pd.NamedAgg(column="l_suppkey", aggfunc="first"),
        )

        jn1 = supplier_ds.merge(l1, left_on="s_suppkey", right_on="l_suppkey")
        jn2 = jn1.merge(orders_ds, left_on="l_orderkey", right_on="o_orderkey")
        jn3 = jn2[
            (jn2["o_orderstatus"] == "F")
            & (jn2["l_orderkey"].isin(orders_with_other_suppliers))
        ]
        jn4 = jn3.merge(nation_ds, left_on="s_nationkey", right_on="n_nationkey")
        jn5 = jn4[jn4["n_name"] == var1]
        jn6 = jn5.merge(
            other_late_suppliers, left_on="l_orderkey", right_on="l_orderkey", how="left"
        )

        # Filtra NOT EXISTS: verifica se há apenas um suppkey único e é igual ao atual
        jn6 = jn6.copy()
        filt = jn6[
            (jn6["late_suppkey_count"].isna())
            | (
                (jn6["late_suppkey_count"] == 1)
                & (jn6["late_suppkey_unique"] == jn6["s_suppkey"])
            )
        ]

        gb = filt.groupby("s_name", as_index=False)
        agg = gb.agg(numwait=pd.NamedAgg(column="s_name", aggfunc="size"))

        result_df = agg.sort_values(by=["numwait", "s_name"], ascending=[False, True]).head(
            100
        )

        return result_df  # type: ignore[no-any-return]

    utils.run_query(Q_NUM, query)


if __name__ == "__main__":
    q()



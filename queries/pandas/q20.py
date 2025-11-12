from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

import pandas as pd

from queries.pandas import utils

if TYPE_CHECKING:
    pass

Q_NUM = 20


def q() -> None:
    supplier_ds = utils.get_supplier_ds
    nation_ds = utils.get_nation_ds
    part_supp_ds = utils.get_part_supp_ds
    part_ds = utils.get_part_ds
    line_item_ds = utils.get_line_item_ds

    # first call one time to cache in case we don't include the IO times
    supplier_ds()
    nation_ds()
    part_supp_ds()
    part_ds()
    line_item_ds()

    def query() -> pd.DataFrame:
        nonlocal supplier_ds
        nonlocal nation_ds
        nonlocal part_supp_ds
        nonlocal part_ds
        nonlocal line_item_ds
        supplier_ds = supplier_ds()
        nation_ds = nation_ds()
        part_supp_ds = part_supp_ds()
        part_ds = part_ds()
        line_item_ds = line_item_ds()

        var1 = "forest"
        var2 = date(1994, 1, 1)
        var3 = var2 + timedelta(days=365)  # +1 year
        var4 = "CANADA"

        # Partes que começam com var1
        matching_parts = part_ds[part_ds["p_name"].str.startswith(var1, na=False)][
            "p_partkey"
        ]

        # Calcula 0.5 * sum(l_quantity) por partkey e suppkey
        lineitem_filt = line_item_ds[
            (line_item_ds["l_shipdate"] >= var2) & (line_item_ds["l_shipdate"] < var3)
        ]
        lineitem_agg = lineitem_filt.groupby(
            ["l_partkey", "l_suppkey"], as_index=False
        ).agg(half_qty=pd.NamedAgg(column="l_quantity", aggfunc=lambda x: 0.5 * x.sum()))

        # Partsupp com availqty > half_qty
        part_supp_filt = part_supp_ds[
            part_supp_ds["ps_partkey"].isin(matching_parts)
        ]
        jn1 = part_supp_filt.merge(
            lineitem_agg,
            left_on=["ps_partkey", "ps_suppkey"],
            right_on=["l_partkey", "l_suppkey"],
        )
        qualifying_partsupp = jn1[jn1["ps_availqty"] > jn1["half_qty"]]["ps_suppkey"]

        jn2 = supplier_ds[supplier_ds["s_suppkey"].isin(qualifying_partsupp)]
        jn3 = jn2.merge(nation_ds, left_on="s_nationkey", right_on="n_nationkey")
        result_df = jn3[jn3["n_name"] == var4][["s_name", "s_address"]].sort_values(
            by="s_name"
        )

        return result_df  # type: ignore[no-any-return]

    utils.run_query(Q_NUM, query)


if __name__ == "__main__":
    q()



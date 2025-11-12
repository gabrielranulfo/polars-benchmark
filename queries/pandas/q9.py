from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from queries.pandas import utils

if TYPE_CHECKING:
    pass

Q_NUM = 9


def q() -> None:
    part_ds = utils.get_part_ds
    supplier_ds = utils.get_supplier_ds
    line_item_ds = utils.get_line_item_ds
    part_supp_ds = utils.get_part_supp_ds
    orders_ds = utils.get_orders_ds
    nation_ds = utils.get_nation_ds

    # first call one time to cache in case we don't include the IO times
    part_ds()
    supplier_ds()
    line_item_ds()
    part_supp_ds()
    orders_ds()
    nation_ds()

    def query() -> pd.DataFrame:
        nonlocal part_ds
        nonlocal supplier_ds
        nonlocal line_item_ds
        nonlocal part_supp_ds
        nonlocal orders_ds
        nonlocal nation_ds
        part_ds = part_ds()
        supplier_ds = supplier_ds()
        line_item_ds = line_item_ds()
        part_supp_ds = part_supp_ds()
        orders_ds = orders_ds()
        nation_ds = nation_ds()

        var1 = "green"

        jn1 = line_item_ds.merge(part_ds, left_on="l_partkey", right_on="p_partkey")
        jn2 = jn1.merge(
            part_supp_ds,
            left_on=["l_suppkey", "l_partkey"],
            right_on=["ps_suppkey", "ps_partkey"],
        )
        jn3 = jn2.merge(supplier_ds, left_on="l_suppkey", right_on="s_suppkey")
        jn4 = jn3.merge(orders_ds, left_on="l_orderkey", right_on="o_orderkey")
        jn5 = jn4.merge(nation_ds, left_on="s_nationkey", right_on="n_nationkey")

        filt = jn5[jn5["p_name"].str.contains(var1, na=False)]

        filt = filt.copy()
        filt["o_year"] = filt["o_orderdate"].dt.year
        filt["amount"] = (
            filt["l_extendedprice"] * (1 - filt["l_discount"])
            - filt["ps_supplycost"] * filt["l_quantity"]
        )

        gb = filt.groupby(["n_name", "o_year"], as_index=False)
        agg = gb.agg(sum_profit=pd.NamedAgg(column="amount", aggfunc="sum"))

        result_df = agg.rename(columns={"n_name": "nation"})
        result_df = result_df.sort_values(by=["nation", "o_year"], ascending=[True, False])

        return result_df  # type: ignore[no-any-return]

    utils.run_query(Q_NUM, query)


if __name__ == "__main__":
    q()



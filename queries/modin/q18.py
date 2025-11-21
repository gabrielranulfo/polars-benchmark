from __future__ import annotations

import modin.pandas as pd

from queries.modin import utils

Q_NUM = 18


def q() -> None:
    customer_ds = utils.get_customer_ds
    orders_ds = utils.get_orders_ds
    line_item_ds = utils.get_line_item_ds

    # first call one time to cache in case we don't include the IO times
    customer_ds()
    orders_ds()
    line_item_ds()

    def query() -> pd.DataFrame:
        nonlocal customer_ds
        nonlocal orders_ds
        nonlocal line_item_ds
        customer_ds = customer_ds()
        orders_ds = orders_ds()
        line_item_ds = line_item_ds()

        var1 = 300

        # Encontra orderkeys com quantidade total > var1
        large_orders = line_item_ds.groupby("l_orderkey", as_index=False).agg(
            total_qty=pd.NamedAgg(column="l_quantity", aggfunc="sum")
        )
        large_orders = large_orders[large_orders["total_qty"] > var1]["l_orderkey"]

        jn1 = customer_ds.merge(orders_ds, left_on="c_custkey", right_on="o_custkey")
        jn2 = jn1[jn1["o_orderkey"].isin(large_orders)]
        jn3 = jn2.merge(line_item_ds, left_on="o_orderkey", right_on="l_orderkey")

        gb = jn3.groupby(
            ["c_name", "c_custkey", "o_orderkey", "o_orderdate", "o_totalprice"],
            as_index=False,
        )
        agg = gb.agg(l_quantity=pd.NamedAgg(column="l_quantity", aggfunc="sum"))

        result_df = agg.sort_values(
            by=["o_totalprice", "o_orderdate"], ascending=[False, True]
        ).head(100)

        return result_df

    utils.run_query(Q_NUM, query)


if __name__ == "__main__":
    q()









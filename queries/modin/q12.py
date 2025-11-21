from __future__ import annotations

from datetime import date, timedelta

import modin.pandas as pd

from queries.modin import utils

Q_NUM = 12


def q() -> None:
    orders_ds = utils.get_orders_ds
    line_item_ds = utils.get_line_item_ds

    # first call one time to cache in case we don't include the IO times
    orders_ds()
    line_item_ds()

    def query() -> pd.DataFrame:
        nonlocal orders_ds
        nonlocal line_item_ds
        orders_ds = orders_ds()
        line_item_ds = line_item_ds()

        var1 = "MAIL"
        var2 = "SHIP"
        var3 = date(1994, 1, 1)
        var4 = var3 + timedelta(days=365)  # +1 year

        jn = orders_ds.merge(line_item_ds, left_on="o_orderkey", right_on="l_orderkey")

        filt = jn[
            (jn["l_shipmode"].isin([var1, var2]))
            & (jn["l_commitdate"] < jn["l_receiptdate"])
            & (jn["l_shipdate"] < jn["l_commitdate"])
            & (jn["l_receiptdate"] >= var3)
            & (jn["l_receiptdate"] < var4)
        ]

        filt = filt.copy()
        filt["high_line_count"] = (
            (filt["o_orderpriority"] == "1-URGENT")
            | (filt["o_orderpriority"] == "2-HIGH")
        ).astype(int)
        filt["low_line_count"] = (
            (filt["o_orderpriority"] != "1-URGENT")
            & (filt["o_orderpriority"] != "2-HIGH")
        ).astype(int)

        gb = filt.groupby("l_shipmode", as_index=False)
        agg = gb.agg(
            high_line_count=pd.NamedAgg(column="high_line_count", aggfunc="sum"),
            low_line_count=pd.NamedAgg(column="low_line_count", aggfunc="sum"),
        )

        result_df = agg.sort_values(by="l_shipmode")

        return result_df

    utils.run_query(Q_NUM, query)


if __name__ == "__main__":
    q()









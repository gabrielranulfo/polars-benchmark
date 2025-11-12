from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

import pandas as pd

from queries.pandas import utils

if TYPE_CHECKING:
    pass

Q_NUM = 15


def q() -> None:
    line_item_ds = utils.get_line_item_ds
    supplier_ds = utils.get_supplier_ds

    # first call one time to cache in case we don't include the IO times
    line_item_ds()
    supplier_ds()

    def query() -> pd.DataFrame:
        nonlocal line_item_ds
        nonlocal supplier_ds
        line_item_ds = line_item_ds()
        supplier_ds = supplier_ds()

        var1 = date(1996, 1, 1)
        var2 = var1 + timedelta(days=90)  # +3 months

        # Cria a "view" revenue
        revenue_filt = line_item_ds[
            (line_item_ds["l_shipdate"] >= var1) & (line_item_ds["l_shipdate"] < var2)
        ]
        revenue_filt = revenue_filt.copy()
        revenue_filt["total_revenue"] = revenue_filt["l_extendedprice"] * (
            1 - revenue_filt["l_discount"]
        )

        revenue = revenue_filt.groupby("l_suppkey", as_index=False).agg(
            total_revenue=pd.NamedAgg(column="total_revenue", aggfunc="sum")
        )
        revenue = revenue.rename(columns={"l_suppkey": "supplier_no"})

        max_revenue = revenue["total_revenue"].max()

        jn = supplier_ds.merge(
            revenue, left_on="s_suppkey", right_on="supplier_no"
        )
        result_df = jn[jn["total_revenue"] == max_revenue][
            ["s_suppkey", "s_name", "s_address", "s_phone", "total_revenue"]
        ].sort_values(by="s_suppkey")

        return result_df  # type: ignore[no-any-return]

    utils.run_query(Q_NUM, query)


if __name__ == "__main__":
    q()



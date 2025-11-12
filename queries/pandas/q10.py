from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

import pandas as pd

from queries.pandas import utils

if TYPE_CHECKING:
    pass

Q_NUM = 10


def q() -> None:
    customer_ds = utils.get_customer_ds
    orders_ds = utils.get_orders_ds
    line_item_ds = utils.get_line_item_ds
    nation_ds = utils.get_nation_ds

    # first call one time to cache in case we don't include the IO times
    customer_ds()
    orders_ds()
    line_item_ds()
    nation_ds()

    def query() -> pd.DataFrame:
        nonlocal customer_ds
        nonlocal orders_ds
        nonlocal line_item_ds
        nonlocal nation_ds
        customer_ds = customer_ds()
        orders_ds = orders_ds()
        line_item_ds = line_item_ds()
        nation_ds = nation_ds()

        var1 = date(1993, 10, 1)
        var2 = var1 + timedelta(days=90)  # +3 months

        jn1 = customer_ds.merge(orders_ds, left_on="c_custkey", right_on="o_custkey")
        jn2 = jn1.merge(line_item_ds, left_on="o_orderkey", right_on="l_orderkey")
        jn3 = jn2.merge(nation_ds, left_on="c_nationkey", right_on="n_nationkey")

        filt = jn3[
            (jn3["o_orderdate"] >= var1)
            & (jn3["o_orderdate"] < var2)
            & (jn3["l_returnflag"] == "R")
        ]

        filt = filt.copy()
        filt["revenue"] = filt["l_extendedprice"] * (1 - filt["l_discount"])

        gb = filt.groupby(
            [
                "c_custkey",
                "c_name",
                "c_acctbal",
                "c_phone",
                "n_name",
                "c_address",
                "c_comment",
            ],
            as_index=False,
        )
        agg = gb.agg(revenue=pd.NamedAgg(column="revenue", aggfunc="sum"))

        result_df = agg.sort_values(by="revenue", ascending=False).head(20)

        return result_df  # type: ignore[no-any-return]

    utils.run_query(Q_NUM, query)


if __name__ == "__main__":
    q()



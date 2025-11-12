from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from queries.pandas import utils

if TYPE_CHECKING:
    pass

Q_NUM = 13


def q() -> None:
    customer_ds = utils.get_customer_ds
    orders_ds = utils.get_orders_ds

    # first call one time to cache in case we don't include the IO times
    customer_ds()
    orders_ds()

    def query() -> pd.DataFrame:
        nonlocal customer_ds
        nonlocal orders_ds
        customer_ds = customer_ds()
        orders_ds = orders_ds()

        var1 = "special"
        var2 = "requests"

        # Filtra orders antes do left join
        orders_filtered = orders_ds[
            ~orders_ds["o_comment"].str.contains(f"{var1}{var2}", na=False)
        ]

        # Left join
        jn = customer_ds.merge(
            orders_filtered, left_on="c_custkey", right_on="o_custkey", how="left"
        )

        gb1 = jn.groupby("c_custkey", as_index=False)
        c_orders = gb1.agg(c_count=pd.NamedAgg(column="o_orderkey", aggfunc="count"))

        gb2 = c_orders.groupby("c_count", as_index=False)
        agg = gb2.agg(custdist=pd.NamedAgg(column="c_custkey", aggfunc="size"))

        result_df = agg.sort_values(by=["custdist", "c_count"], ascending=[False, False])

        return result_df  # type: ignore[no-any-return]

    utils.run_query(Q_NUM, query)


if __name__ == "__main__":
    q()



from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from queries.pandas import utils

if TYPE_CHECKING:
    pass

Q_NUM = 17


def q() -> None:
    line_item_ds = utils.get_line_item_ds
    part_ds = utils.get_part_ds

    # first call one time to cache in case we don't include the IO times
    line_item_ds()
    part_ds()

    def query() -> pd.DataFrame:
        nonlocal line_item_ds
        nonlocal part_ds
        line_item_ds = line_item_ds()
        part_ds = part_ds()

        var1 = "Brand#23"
        var2 = "MED CASE"

        # Calcula a média de quantidade por partkey
        avg_qty = line_item_ds.groupby("l_partkey", as_index=False).agg(
            avg_qty=pd.NamedAgg(column="l_quantity", aggfunc="mean")
        )

        part_filt = part_ds[(part_ds["p_brand"] == var1) & (part_ds["p_container"] == var2)]

        jn1 = part_filt.merge(line_item_ds, left_on="p_partkey", right_on="l_partkey")
        jn2 = jn1.merge(avg_qty, left_on="p_partkey", right_on="l_partkey")

        filt = jn2[jn2["l_quantity"] < 0.2 * jn2["avg_qty"]]

        avg_yearly = filt["l_extendedprice"].sum() / 7.0

        result_df = pd.DataFrame({"avg_yearly": [avg_yearly]})

        return result_df  # type: ignore[no-any-return]

    utils.run_query(Q_NUM, query)


if __name__ == "__main__":
    q()



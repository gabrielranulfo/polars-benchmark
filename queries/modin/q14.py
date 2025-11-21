from __future__ import annotations

from datetime import date, timedelta

import modin.pandas as pd

from queries.modin import utils

Q_NUM = 14


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

        var1 = date(1995, 9, 1)
        var2 = var1 + timedelta(days=30)  # +1 month

        jn = line_item_ds.merge(part_ds, left_on="l_partkey", right_on="p_partkey")

        filt = jn[(jn["l_shipdate"] >= var1) & (jn["l_shipdate"] < var2)]

        filt = filt.copy()
        filt["disc_price"] = filt["l_extendedprice"] * (1 - filt["l_discount"])
        filt["promo_disc_price"] = filt.apply(
            lambda row: row["disc_price"]
            if str(row["p_type"]).startswith("PROMO")
            else 0,
            axis=1,
        )

        promo_revenue = (
            100.00 * filt["promo_disc_price"].sum() / filt["disc_price"].sum()
        )

        result_df = pd.DataFrame({"promo_revenue": [promo_revenue]})

        return result_df

    utils.run_query(Q_NUM, query)


if __name__ == "__main__":
    q()









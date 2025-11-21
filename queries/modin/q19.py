from __future__ import annotations

import modin.pandas as pd

from queries.modin import utils

Q_NUM = 19


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

        var1 = "Brand#12"
        var4 = 1
        var2 = "Brand#23"
        var5 = 10
        var3 = "Brand#34"
        var6 = 20

        jn = line_item_ds.merge(part_ds, left_on="l_partkey", right_on="p_partkey")

        filt = jn[
            (
                (jn["p_brand"] == var1)
                & (jn["p_container"].isin(["SM CASE", "SM BOX", "SM PACK", "SM PKG"]))
                & (jn["l_quantity"] >= var4)
                & (jn["l_quantity"] <= var4 + 10)
                & (jn["p_size"] >= 1)
                & (jn["p_size"] <= 5)
                & (jn["l_shipmode"].isin(["AIR", "AIR REG"]))
                & (jn["l_shipinstruct"] == "DELIVER IN PERSON")
            )
            | (
                (jn["p_brand"] == var2)
                & (jn["p_container"].isin(["MED BAG", "MED BOX", "MED PKG", "MED PACK"]))
                & (jn["l_quantity"] >= var5)
                & (jn["l_quantity"] <= var5 + 10)
                & (jn["p_size"] >= 1)
                & (jn["p_size"] <= 10)
                & (jn["l_shipmode"].isin(["AIR", "AIR REG"]))
                & (jn["l_shipinstruct"] == "DELIVER IN PERSON")
            )
            | (
                (jn["p_brand"] == var3)
                & (jn["p_container"].isin(["LG CASE", "LG BOX", "LG PACK", "LG PKG"]))
                & (jn["l_quantity"] >= var6)
                & (jn["l_quantity"] <= var6 + 10)
                & (jn["p_size"] >= 1)
                & (jn["p_size"] <= 15)
                & (jn["l_shipmode"].isin(["AIR", "AIR REG"]))
                & (jn["l_shipinstruct"] == "DELIVER IN PERSON")
            )
        ]

        filt = filt.copy()
        filt["revenue"] = filt["l_extendedprice"] * (1 - filt["l_discount"])

        revenue = filt["revenue"].sum()

        result_df = pd.DataFrame({"revenue": [revenue]})

        return result_df

    utils.run_query(Q_NUM, query)


if __name__ == "__main__":
    q()









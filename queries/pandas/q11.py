from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from queries.pandas import utils

if TYPE_CHECKING:
    pass

Q_NUM = 11


def q() -> None:
    part_supp_ds = utils.get_part_supp_ds
    supplier_ds = utils.get_supplier_ds
    nation_ds = utils.get_nation_ds

    # first call one time to cache in case we don't include the IO times
    part_supp_ds()
    supplier_ds()
    nation_ds()

    def query() -> pd.DataFrame:
        nonlocal part_supp_ds
        nonlocal supplier_ds
        nonlocal nation_ds
        part_supp_ds = part_supp_ds()
        supplier_ds = supplier_ds()
        nation_ds = nation_ds()

        var1 = "GERMANY"
        var2 = 0.0001

        jn1 = part_supp_ds.merge(supplier_ds, left_on="ps_suppkey", right_on="s_suppkey")
        jn2 = jn1.merge(nation_ds, left_on="s_nationkey", right_on="n_nationkey")
        filt = jn2[jn2["n_name"] == var1]

        filt = filt.copy()
        filt["value"] = filt["ps_supplycost"] * filt["ps_availqty"]

        # Calcula o threshold
        total_value = filt["value"].sum()
        threshold = total_value * var2

        gb = filt.groupby("ps_partkey", as_index=False)
        agg = gb.agg(value=pd.NamedAgg(column="value", aggfunc="sum"))

        result_df = agg[agg["value"] > threshold].sort_values(
            by="value", ascending=False
        )

        return result_df  # type: ignore[no-any-return]

    utils.run_query(Q_NUM, query)


if __name__ == "__main__":
    q()



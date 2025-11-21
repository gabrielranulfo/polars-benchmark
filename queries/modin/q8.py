from __future__ import annotations

from datetime import date

import modin.pandas as pd

from queries.modin import utils

Q_NUM = 8


def q() -> None:
    part_ds = utils.get_part_ds
    supplier_ds = utils.get_supplier_ds
    line_item_ds = utils.get_line_item_ds
    orders_ds = utils.get_orders_ds
    customer_ds = utils.get_customer_ds
    nation_ds = utils.get_nation_ds
    region_ds = utils.get_region_ds

    # first call one time to cache in case we don't include the IO times
    part_ds()
    supplier_ds()
    line_item_ds()
    orders_ds()
    customer_ds()
    nation_ds()
    region_ds()

    def query() -> pd.DataFrame:
        nonlocal part_ds
        nonlocal supplier_ds
        nonlocal line_item_ds
        nonlocal orders_ds
        nonlocal customer_ds
        nonlocal nation_ds
        nonlocal region_ds
        part_ds = part_ds()
        supplier_ds = supplier_ds()
        line_item_ds = line_item_ds()
        orders_ds = orders_ds()
        customer_ds = customer_ds()
        nation_ds = nation_ds()
        region_ds = region_ds()

        var1 = "BRAZIL"  # :1 - nação do fornecedor
        var2 = "AMERICA"  # :2 - região
        var3 = "ECONOMY ANODIZED STEEL"  # :3 - tipo de peça
        var4 = date(1995, 1, 1)
        var5 = date(1996, 12, 31)

        # Filtra a região
        region_filtered = region_ds[region_ds["r_name"] == var2]

        # Filtra a nação do fornecedor
        n2 = nation_ds[nation_ds["n_name"] == var1]

        # Filtra o tipo de peça
        part_filtered = part_ds[part_ds["p_type"] == var3]

        # Faz os joins conforme a query SQL
        jn1 = part_filtered.merge(line_item_ds, left_on="p_partkey", right_on="l_partkey")
        jn2 = jn1.merge(supplier_ds, left_on="l_suppkey", right_on="s_suppkey")
        jn3 = jn2.merge(orders_ds, left_on="l_orderkey", right_on="o_orderkey")
        jn4 = jn3.merge(customer_ds, left_on="o_custkey", right_on="c_custkey")
        jn5 = jn4.merge(nation_ds, left_on="c_nationkey", right_on="n_nationkey")
        jn5 = jn5.rename(columns={"n_name": "cust_nation"})
        jn6 = jn5.merge(region_filtered, left_on="n_regionkey", right_on="r_regionkey")
        jn7 = jn6.merge(n2, left_on="s_nationkey", right_on="n_nationkey")
        jn7 = jn7.rename(columns={"n_name": "supp_nation"})

        # Filtra por data
        all_nations = jn7[
            (jn7["o_orderdate"] >= var4) & (jn7["o_orderdate"] <= var5)
        ]

        # Calcula volume e ano
        all_nations = all_nations.copy()
        all_nations["o_year"] = all_nations["o_orderdate"].dt.year
        all_nations["volume"] = all_nations["l_extendedprice"] * (
            1 - all_nations["l_discount"]
        )

        # Calcula participação de mercado
        all_nations = all_nations.copy()
        all_nations["nation_volume"] = all_nations.apply(
            lambda row: row["volume"] if row["supp_nation"] == var1 else 0, axis=1
        )

        def calc_mkt_share(group):
            o_year_val = group.name  # Nome do grupo é o valor de o_year
            nation_vol = group[group["supp_nation"] == var1]["volume"].sum()
            total_vol = group["volume"].sum()
            mkt_share = nation_vol / total_vol if total_vol > 0 else 0
            return pd.Series({"o_year": o_year_val, "mkt_share": mkt_share})

        gb = all_nations.groupby("o_year")
        result_df = gb.apply(calc_mkt_share, include_groups=False).reset_index(drop=True)

        result_df = result_df.sort_values(by="o_year")

        return result_df

    utils.run_query(Q_NUM, query)


if __name__ == "__main__":
    q()









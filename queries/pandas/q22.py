from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from queries.pandas import utils

if TYPE_CHECKING:
    pass

Q_NUM = 22


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

        var1 = "13"
        var2 = "31"
        var3 = "23"
        var4 = "29"
        var5 = "30"
        var6 = "18"
        var7 = "17"

        country_codes = [var1, var2, var3, var4, var5, var6, var7]

        # Extrai código do país do telefone
        customer_ds = customer_ds.copy()
        customer_ds["cntrycode"] = customer_ds["c_phone"].str[:2]

        # Calcula média de c_acctbal para países específicos com c_acctbal > 0
        customer_filt = customer_ds[
            (customer_ds["cntrycode"].isin(country_codes))
            & (customer_ds["c_acctbal"] > 0.00)
        ]
        avg_acctbal = customer_filt["c_acctbal"].mean()

        # Clientes sem ordens
        customers_with_orders = orders_ds["o_custkey"].unique()

        # Filtra clientes
        result_filt = customer_ds[
            (customer_ds["cntrycode"].isin(country_codes))
            & (customer_ds["c_acctbal"] > avg_acctbal)
            & (~customer_ds["c_custkey"].isin(customers_with_orders))
        ]

        gb = result_filt.groupby("cntrycode", as_index=False)
        agg = gb.agg(
            numcust=pd.NamedAgg(column="c_custkey", aggfunc="size"),
            totacctbal=pd.NamedAgg(column="c_acctbal", aggfunc="sum"),
        )

        result_df = agg.sort_values(by="cntrycode")

        return result_df  # type: ignore[no-any-return]

    utils.run_query(Q_NUM, query)


if __name__ == "__main__":
    q()



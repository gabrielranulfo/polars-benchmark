from __future__ import annotations

import pandas as pd

from queries.dask import utils

Q_NUM = 22


def q() -> None:
    customer_ds = utils.get_customer_ds
    orders_ds = utils.get_orders_ds
    
    # first call one time to cache in case we don't include the IO times
    customer_ds()
    orders_ds()

    def query() -> pd.DataFrame:
        nonlocal customer_ds, orders_ds
        
        customer_ds = customer_ds()
        orders_ds = orders_ds()

        # Parâmetros da query - códigos de país
        countries = ['13', '31', '23', '29', '30', '18', '17']  # :1 a :7

        # Subquery: calcular média de c_acctbal para critério
        customer_filt_for_avg = customer_ds[
            (customer_ds['c_acctbal'] > 0.00) &
            (customer_ds['c_phone'].str.slice(0, 2).isin(countries))
        ]
        avg_acctbal = customer_filt_for_avg['c_acctbal'].mean().compute()

        # Subquery NOT EXISTS: customers sem orders
        # Obter lista de customers que têm orders
        customers_with_orders = orders_ds['o_custkey'].drop_duplicates().compute().tolist()

        # Filtrar customers principais
        customer_filt = customer_ds[
            (customer_ds['c_phone'].str.slice(0, 2).isin(countries)) &
            (customer_ds['c_acctbal'] > avg_acctbal) &
            (~customer_ds['c_custkey'].isin(customers_with_orders))
        ]

        # Criar coluna cntrycode
        customer_filt = customer_filt.copy()
        customer_filt['cntrycode'] = customer_filt['c_phone'].str.slice(0, 2)

        # Agrupar por cntrycode
        gb = customer_filt.groupby('cntrycode')
        agg_df = gb.agg(
            numcust=pd.NamedAgg(column='c_custkey', aggfunc='size'),
            totacctbal=pd.NamedAgg(column='c_acctbal', aggfunc='sum')
        ).reset_index()

        # Ordenar por cntrycode
        result_df = agg_df.sort_values('cntrycode')

        return result_df.compute()

    utils.run_query(Q_NUM, query)


if __name__ == "__main__":
    q()
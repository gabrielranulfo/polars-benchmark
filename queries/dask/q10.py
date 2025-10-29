from __future__ import annotations

from datetime import date
from dateutil.relativedelta import relativedelta

import pandas as pd

from queries.dask import utils

Q_NUM = 10


def q() -> None:
    line_item_ds = utils.get_line_item_ds
    orders_ds = utils.get_orders_ds
    customer_ds = utils.get_customer_ds
    nation_ds = utils.get_nation_ds
    
    # first call one time to cache in case we don't include the IO times
    line_item_ds()
    orders_ds()
    customer_ds()
    nation_ds()

    def query() -> pd.DataFrame:
        nonlocal line_item_ds, orders_ds, customer_ds, nation_ds
        
        line_item_ds = line_item_ds()
        orders_ds = orders_ds()
        customer_ds = customer_ds()
        nation_ds = nation_ds()

        # Parâmetro da query
        start_date = date(1993, 10, 1)  # :1

        # Calcular data final (start_date + 3 meses)
        end_date = start_date + relativedelta(months=3)

        # Filtrar lineitem por returnflag = 'R'
        lineitem_filt = line_item_ds[line_item_ds['l_returnflag'] == 'R']

        # Filtrar orders por período
        orders_filt = orders_ds[
            (orders_ds['o_orderdate'] >= start_date) & 
            (orders_ds['o_orderdate'] < end_date)
        ]

        # Juntar customer com nation
        customer_nation = customer_ds.merge(
            nation_ds[['n_nationkey', 'n_name']],
            left_on='c_nationkey',
            right_on='n_nationkey',
            how='inner'
        ).rename(columns={'n_name': 'n_name'})

        # Juntar orders com customer (que já tem nation)
        orders_customer = orders_filt.merge(
            customer_nation[
                ['c_custkey', 'c_name', 'c_acctbal', 'c_address', 
                 'c_phone', 'c_comment', 'n_name']
            ],
            left_on='o_custkey',
            right_on='c_custkey',
            how='inner'
        )

        # Juntar com lineitem filtrado
        final_df = orders_customer.merge(
            lineitem_filt[['l_orderkey', 'l_extendedprice', 'l_discount']],
            left_on='o_orderkey',
            right_on='l_orderkey',
            how='inner'
        )

        # Calcular revenue
        final_df['revenue'] = final_df['l_extendedprice'] * (1 - final_df['l_discount'])

        # Agrupar pelas colunas especificadas
        gb = final_df.groupby([
            'c_custkey', 'c_name', 'c_acctbal', 'c_phone', 
            'n_name', 'c_address', 'c_comment'
        ])
        
        agg_df = gb.agg(
            revenue=pd.NamedAgg(column='revenue', aggfunc='sum')
        ).reset_index()

        # Ordenar por revenue descendente
        result_df = agg_df.sort_values('revenue', ascending=False)

        # Selecionar colunas na ordem do SQL
        result_df = result_df[[
            'c_custkey', 'c_name', 'revenue', 'c_acctbal', 
            'n_name', 'c_address', 'c_phone', 'c_comment'
        ]]

        return result_df.compute()

    utils.run_query(Q_NUM, query)


if __name__ == "__main__":
    q()
from __future__ import annotations

import pandas as pd

from queries.dask import utils

Q_NUM = 18


def q() -> None:
    line_item_ds = utils.get_line_item_ds
    orders_ds = utils.get_orders_ds
    customer_ds = utils.get_customer_ds
    
    # first call one time to cache in case we don't include the IO times
    line_item_ds()
    orders_ds()
    customer_ds()

    def query() -> pd.DataFrame:
        nonlocal line_item_ds, orders_ds, customer_ds
        
        line_item_ds = line_item_ds()
        orders_ds = orders_ds()
        customer_ds = customer_ds()

        # Parâmetro da query
        quantity_threshold = 300  # :1

        # Subquery: orders com soma de quantity > threshold
        order_quantities = line_item_ds.groupby('l_orderkey')['l_quantity'].sum().reset_index()
        large_orders = order_quantities[order_quantities['l_quantity'] > quantity_threshold]
        
        # Converter para lista para usar no filtro IN
        large_order_keys = large_orders['l_orderkey'].compute().tolist()

        # Filtrar orders que estão na subquery (IN)
        orders_filt = orders_ds[orders_ds['o_orderkey'].isin(large_order_keys)]

        # Juntar customer com orders filtrados
        customer_orders = customer_ds.merge(
            orders_filt[['o_orderkey', 'o_custkey', 'o_orderdate', 'o_totalprice']],
            left_on='c_custkey',
            right_on='o_custkey',
            how='inner'
        )

        # Juntar com lineitem para obter as quantidades
        customer_orders_lineitem = customer_orders.merge(
            line_item_ds[['l_orderkey', 'l_quantity']],
            left_on='o_orderkey',
            right_on='l_orderkey',
            how='inner'
        )

        # Agrupar pelas colunas especificadas e somar as quantidades
        gb = customer_orders_lineitem.groupby([
            'c_name', 'c_custkey', 'o_orderkey', 'o_orderdate', 'o_totalprice'
        ])
        
        agg_df = gb.agg(
            sum_l_quantity=pd.NamedAgg(column='l_quantity', aggfunc='sum')
        ).reset_index()

        # Ordenar por o_totalprice descendente, o_orderdate ascendente
        result_df = agg_df.sort_values(
            ['o_totalprice', 'o_orderdate'],
            ascending=[False, True]
        )

        # Selecionar colunas na ordem do SQL
        result_df = result_df[[
            'c_name', 'c_custkey', 'o_orderkey', 'o_orderdate', 
            'o_totalprice', 'sum_l_quantity'
        ]]

        return result_df.compute()

    utils.run_query(Q_NUM, query)


if __name__ == "__main__":
    q()
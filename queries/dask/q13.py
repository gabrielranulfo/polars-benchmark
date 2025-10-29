from __future__ import annotations

import pandas as pd

from queries.dask import utils

Q_NUM = 13


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

        # Parâmetros da query
        word1 = 'special'  # :1
        word2 = 'requests'  # :2

        # Filtrar orders - excluir os que contêm o padrão no comment
        orders_filt = orders_ds[~orders_ds['o_comment'].str.contains(
            f'{word1}.*{word2}', case=False, na=False, regex=True
        )]

        # LEFT JOIN: customer com orders filtrado
        customer_orders = customer_ds.merge(
            orders_filt[['o_custkey', 'o_orderkey']],
            left_on='c_custkey',
            right_on='o_custkey',
            how='left'
        )

        # CORREÇÃO: Usar isnull() em vez de notna() e converter para inteiro
        customer_orders = customer_orders.copy()
        
        # Marcar se tem order ou não (1 se não for nulo, 0 se for nulo)
        customer_orders['has_order'] = (~customer_orders['o_orderkey'].isnull()).astype(int)
        
        # Primeiro agrupamento: contar orders por customer
        gb1 = customer_orders.groupby('c_custkey')
        customer_counts = gb1.agg(
            c_count=pd.NamedAgg(column='has_order', aggfunc='sum')
        ).reset_index()

        # Segundo agrupamento: distribuição dos counts
        gb2 = customer_counts.groupby('c_count')
        custdist_df = gb2.agg(
            custdist=pd.NamedAgg(column='c_custkey', aggfunc='size')
        ).reset_index()

        # Ordenar por custdist descendente, c_count descendente
        result_df = custdist_df.sort_values(
            ['custdist', 'c_count'], 
            ascending=[False, False]
        )

        return result_df.compute()

    utils.run_query(Q_NUM, query)


if __name__ == "__main__":
    q()
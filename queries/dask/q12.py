from __future__ import annotations

from datetime import date
from dateutil.relativedelta import relativedelta

import pandas as pd

from queries.dask import utils

Q_NUM = 12


def q() -> None:
    line_item_ds = utils.get_line_item_ds
    orders_ds = utils.get_orders_ds
    
    # first call one time to cache in case we don't include the IO times
    line_item_ds()
    orders_ds()

    def query() -> pd.DataFrame:
        nonlocal line_item_ds, orders_ds
        
        line_item_ds = line_item_ds()
        orders_ds = orders_ds()

        # Parâmetros da query
        shipmode1 = 'MAIL'  # :1
        shipmode2 = 'SHIP'  # :2
        start_date = date(1994, 1, 1)  # :3

        # Calcular data final (start_date + 1 ano)
        end_date = start_date + relativedelta(years=1)

        # Filtrar lineitem pelas condições
        lineitem_filt = line_item_ds[
            (line_item_ds['l_shipmode'].isin([shipmode1, shipmode2])) &
            (line_item_ds['l_commitdate'] < line_item_ds['l_receiptdate']) &
            (line_item_ds['l_shipdate'] < line_item_ds['l_commitdate']) &
            (line_item_ds['l_receiptdate'] >= start_date) &
            (line_item_ds['l_receiptdate'] < end_date)
        ]

        # Juntar com orders
        lineitem_orders = lineitem_filt.merge(
            orders_ds[['o_orderkey', 'o_orderpriority']],
            left_on='l_orderkey',
            right_on='o_orderkey',
            how='inner'
        )

        # Calcular as contagens condicionais
        lineitem_orders = lineitem_orders.copy()
        
        # High priority count
        lineitem_orders['high_line_count'] = lineitem_orders['o_orderpriority'].isin([
            '1-URGENT', '2-HIGH'
        ]).astype(int)
        
        # Low priority count  
        lineitem_orders['low_line_count'] = (~lineitem_orders['o_orderpriority'].isin([
            '1-URGENT', '2-HIGH'
        ])).astype(int)

        # Agrupar por l_shipmode
        gb = lineitem_orders.groupby('l_shipmode')
        agg_df = gb.agg(
            high_line_count=pd.NamedAgg(column='high_line_count', aggfunc='sum'),
            low_line_count=pd.NamedAgg(column='low_line_count', aggfunc='sum')
        ).reset_index()

        # Ordenar por l_shipmode
        result_df = agg_df.sort_values('l_shipmode')

        return result_df.compute()

    utils.run_query(Q_NUM, query)


if __name__ == "__main__":
    q()
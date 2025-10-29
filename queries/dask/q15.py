from __future__ import annotations

from datetime import date
from dateutil.relativedelta import relativedelta

import pandas as pd

from queries.dask import utils

Q_NUM = 15


def q() -> None:
    line_item_ds = utils.get_line_item_ds
    supplier_ds = utils.get_supplier_ds
    
    # first call one time to cache in case we don't include the IO times
    line_item_ds()
    supplier_ds()

    def query() -> pd.DataFrame:
        nonlocal line_item_ds, supplier_ds
        
        line_item_ds = line_item_ds()
        supplier_ds = supplier_ds()

        # Parâmetro da query
        start_date = date(1996, 1, 1)  # :1

        # Calcular data final (start_date + 3 meses)
        end_date = start_date + relativedelta(months=3)

        # Filtrar lineitem por período de shipdate
        lineitem_filt = line_item_ds[
            (line_item_ds['l_shipdate'] >= start_date) & 
            (line_item_ds['l_shipdate'] < end_date)
        ]

        # Criar a "view" revenue (subquery)
        # Calcular revenue para cada linha
        lineitem_filt = lineitem_filt.copy()
        lineitem_filt['revenue'] = (
            lineitem_filt['l_extendedprice'] * (1 - lineitem_filt['l_discount'])
        )

        # Agrupar por l_suppkey e calcular total_revenue
        gb_revenue = lineitem_filt.groupby('l_suppkey')
        revenue_view = gb_revenue.agg(
            total_revenue=pd.NamedAgg(column='revenue', aggfunc='sum')
        ).reset_index().rename(columns={'l_suppkey': 'supplier_no'})

        # Encontrar o máximo total_revenue
        max_revenue = revenue_view['total_revenue'].max().compute()

        # Filtrar suppliers com total_revenue igual ao máximo
        top_suppliers = revenue_view[revenue_view['total_revenue'] == max_revenue]

        # Juntar com supplier para obter os detalhes
        result_df = top_suppliers.merge(
            supplier_ds,
            left_on='supplier_no',
            right_on='s_suppkey',
            how='inner'
        )

        # Selecionar colunas na ordem do SQL
        result_df = result_df[[
            's_suppkey', 's_name', 's_address', 's_phone', 'total_revenue'
        ]]

        # Ordenar por s_suppkey
        result_df = result_df.sort_values('s_suppkey')

        return result_df.compute()

    utils.run_query(Q_NUM, query)


if __name__ == "__main__":
    q()
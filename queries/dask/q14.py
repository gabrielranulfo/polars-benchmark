from __future__ import annotations

from datetime import date
from dateutil.relativedelta import relativedelta

import pandas as pd

from queries.dask import utils

Q_NUM = 14


def q() -> None:
    line_item_ds = utils.get_line_item_ds
    part_ds = utils.get_part_ds
    
    # first call one time to cache in case we don't include the IO times
    line_item_ds()
    part_ds()

    def query() -> pd.DataFrame:
        nonlocal line_item_ds, part_ds
        
        line_item_ds = line_item_ds()
        part_ds = part_ds()

        # Parâmetro da query
        start_date = date(1995, 9, 1)  # :1

        # Calcular data final (start_date + 1 mês)
        end_date = start_date + relativedelta(months=1)

        # Filtrar lineitem por período de shipdate
        lineitem_filt = line_item_ds[
            (line_item_ds['l_shipdate'] >= start_date) & 
            (line_item_ds['l_shipdate'] < end_date)
        ]

        # Juntar lineitem com part
        lineitem_part = lineitem_filt.merge(
            part_ds[['p_partkey', 'p_type']],
            left_on='l_partkey',
            right_on='p_partkey',
            how='inner'
        )

        # Calcular revenue para cada linha
        lineitem_part = lineitem_part.copy()
        lineitem_part['revenue'] = lineitem_part['l_extendedprice'] * (1 - lineitem_part['l_discount'])
        
        # Calcular promo_revenue (revenue apenas para PROMO types)
        lineitem_part['promo_revenue'] = lineitem_part.apply(
            lambda x: x['revenue'] if x['p_type'].startswith('PROMO') else 0,
            axis=1,
            meta=('promo_revenue', 'float64')
        )

        # Calcular totais
        total_promo_revenue = lineitem_part['promo_revenue'].sum()
        total_revenue = lineitem_part['revenue'].sum()

        # Calcular porcentagem final
        promo_percentage = (100.00 * total_promo_revenue / total_revenue).compute()

        # Criar DataFrame de resultado
        result_df = pd.DataFrame({
            'promo_revenue': [promo_percentage]
        })

        return result_df

    utils.run_query(Q_NUM, query)


if __name__ == "__main__":
    q()
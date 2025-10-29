from __future__ import annotations

import pandas as pd

from queries.dask import utils

Q_NUM = 17


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

        # Parâmetros da query
        brand = 'Brand#23'  # :1
        container = 'MED BOX'  # :2

        # Filtrar part pela brand e container
        part_filt = part_ds[
            (part_ds['p_brand'] == brand) & 
            (part_ds['p_container'] == container)
        ]

        # Juntar lineitem com part filtrado
        lineitem_part = line_item_ds.merge(
            part_filt[['p_partkey']],
            left_on='l_partkey',
            right_on='p_partkey',
            how='inner'
        )

        # CORREÇÃO: Para a subquery correlacionada, precisamos calcular a média por partkey primeiro
        # Calcular a média de quantidade por partkey em todo o lineitem
        avg_quantity_by_part = line_item_ds.groupby('l_partkey')['l_quantity'].mean().reset_index()
        avg_quantity_by_part = avg_quantity_by_part.rename(columns={'l_quantity': 'avg_quantity'})
        
        # Calcular o threshold (0.2 * avg_quantity) para cada partkey
        avg_quantity_by_part['threshold'] = 0.2 * avg_quantity_by_part['avg_quantity']

        # Juntar com lineitem_part para ter o threshold para cada linha
        lineitem_with_threshold = lineitem_part.merge(
            avg_quantity_by_part[['l_partkey', 'threshold']],
            left_on='l_partkey',
            right_on='l_partkey',
            how='inner'
        )

        # Filtrar linhas onde l_quantity < threshold
        filtered_lineitem = lineitem_with_threshold[
            lineitem_with_threshold['l_quantity'] < lineitem_with_threshold['threshold']
        ]

        # Calcular a soma do extendedprice
        total_extendedprice = filtered_lineitem['l_extendedprice'].sum()

        # Calcular avg_yearly (soma / 7.0)
        avg_yearly = (total_extendedprice / 7.0).compute()

        # Criar DataFrame de resultado
        result_df = pd.DataFrame({
            'avg_yearly': [avg_yearly]
        })

        return result_df

    utils.run_query(Q_NUM, query)


if __name__ == "__main__":
    q()
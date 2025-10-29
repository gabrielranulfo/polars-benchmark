from __future__ import annotations

import pandas as pd

from queries.dask import utils

Q_NUM = 19


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
        brand1 = 'Brand#12'  # :1
        brand2 = 'Brand#23'  # :2  
        brand3 = 'Brand#34'  # :3
        quantity1 = 1  # :4
        quantity2 = 10  # :5
        quantity3 = 20  # :6

        # Containers para cada brand
        containers1 = ['SM CASE', 'SM BOX', 'SM PACK', 'SM PKG']
        containers2 = ['MED BAG', 'MED BOX', 'MED PKG', 'MED PACK']
        containers3 = ['LG CASE', 'LG BOX', 'LG PACK', 'LG PKG']

        # Ship modes e instruct comuns
        ship_modes = ['AIR', 'AIR REG']
        ship_instruct = 'DELIVER IN PERSON'

        # Juntar lineitem com part
        lineitem_part = line_item_ds.merge(
            part_ds[['p_partkey', 'p_brand', 'p_container', 'p_size']],
            left_on='l_partkey',
            right_on='p_partkey',
            how='inner'
        )

        # Aplicar as condições OR complexas
        # Primeira condição
        cond1 = (
            (lineitem_part['p_brand'] == brand1) &
            (lineitem_part['p_container'].isin(containers1)) &
            (lineitem_part['l_quantity'] >= quantity1) &
            (lineitem_part['l_quantity'] <= quantity1 + 10) &
            (lineitem_part['p_size'] >= 1) &
            (lineitem_part['p_size'] <= 5) &
            (lineitem_part['l_shipmode'].isin(ship_modes)) &
            (lineitem_part['l_shipinstruct'] == ship_instruct)
        )

        # Segunda condição
        cond2 = (
            (lineitem_part['p_brand'] == brand2) &
            (lineitem_part['p_container'].isin(containers2)) &
            (lineitem_part['l_quantity'] >= quantity2) &
            (lineitem_part['l_quantity'] <= quantity2 + 10) &
            (lineitem_part['p_size'] >= 1) &
            (lineitem_part['p_size'] <= 10) &
            (lineitem_part['l_shipmode'].isin(ship_modes)) &
            (lineitem_part['l_shipinstruct'] == ship_instruct)
        )

        # Terceira condição
        cond3 = (
            (lineitem_part['p_brand'] == brand3) &
            (lineitem_part['p_container'].isin(containers3)) &
            (lineitem_part['l_quantity'] >= quantity3) &
            (lineitem_part['l_quantity'] <= quantity3 + 10) &
            (lineitem_part['p_size'] >= 1) &
            (lineitem_part['p_size'] <= 15) &
            (lineitem_part['l_shipmode'].isin(ship_modes)) &
            (lineitem_part['l_shipinstruct'] == ship_instruct)
        )

        # Combinar as condições com OR
        filtered_data = lineitem_part[cond1 | cond2 | cond3]

        # Calcular revenue para cada linha
        filtered_data = filtered_data.copy()
        filtered_data['revenue'] = (
            filtered_data['l_extendedprice'] * (1 - filtered_data['l_discount'])
        )

        # Calcular soma total do revenue
        total_revenue = filtered_data['revenue'].sum().compute()

        # Criar DataFrame de resultado
        result_df = pd.DataFrame({
            'revenue': [total_revenue]
        })

        return result_df

    utils.run_query(Q_NUM, query)


if __name__ == "__main__":
    q()
from __future__ import annotations

from datetime import date
from dateutil.relativedelta import relativedelta

import pandas as pd

from queries.dask import utils

Q_NUM = 20


def q() -> None:
    supplier_ds = utils.get_supplier_ds
    nation_ds = utils.get_nation_ds
    part_supp_ds = utils.get_part_supp_ds
    part_ds = utils.get_part_ds
    line_item_ds = utils.get_line_item_ds
    
    # first call one time to cache in case we don't include the IO times
    supplier_ds()
    nation_ds()
    part_supp_ds()
    part_ds()
    line_item_ds()

    def query() -> pd.DataFrame:
        nonlocal supplier_ds, nation_ds, part_supp_ds, part_ds, line_item_ds
        
        supplier_ds = supplier_ds()
        nation_ds = nation_ds()
        part_supp_ds = part_supp_ds()
        part_ds = part_ds()
        line_item_ds = line_item_ds()

        # Parâmetros da query
        part_name_pattern = 'forest'  # :1
        start_date = date(1994, 1, 1)  # :2
        nation_name = 'CANADA'  # :3

        # Calcular data final
        end_date = start_date + relativedelta(years=1)

        # Primeira subquery: partkeys com nome começando com o pattern
        part_filt = part_ds[part_ds['p_name'].str.startswith(part_name_pattern)]
        part_keys = part_filt['p_partkey'].compute().tolist()

        # Segunda subquery: calcular soma de quantidades por partkey/suppkey
        lineitem_filt = line_item_ds[
            (line_item_ds['l_shipdate'] >= start_date) & 
            (line_item_ds['l_shipdate'] < end_date)
        ]
        
        # Agrupar por partkey e suppkey para calcular a soma de quantidades
        lineitem_sums = lineitem_filt.groupby(['l_partkey', 'l_suppkey'])['l_quantity'].sum().reset_index()
        lineitem_sums['half_quantity'] = 0.5 * lineitem_sums['l_quantity']

        # Filtrar partsupp: partkey na lista E availqty > half_quantity
        partsupp_filt = part_supp_ds[
            part_supp_ds['ps_partkey'].isin(part_keys)
        ]

        # Juntar partsupp com as somas calculadas
        partsupp_with_sums = partsupp_filt.merge(
            lineitem_sums[['l_partkey', 'l_suppkey', 'half_quantity']],
            left_on=['ps_partkey', 'ps_suppkey'],
            right_on=['l_partkey', 'l_suppkey'],
            how='left'
        )

        # Preencher NaN com 0 para casos onde não há lineitems
        partsupp_with_sums['half_quantity'] = partsupp_with_sums['half_quantity'].fillna(0)

        # Aplicar condição: ps_availqty > half_quantity
        qualified_partsupp = partsupp_with_sums[
            partsupp_with_sums['ps_availqty'] > partsupp_with_sums['half_quantity']
        ]

        # Obter lista de suppkeys qualificados
        qualified_suppkeys = qualified_partsupp['ps_suppkey'].compute().tolist()

        # Filtrar nation pelo nome
        nation_filt = nation_ds[nation_ds['n_name'] == nation_name]

        # Juntar supplier com nation filtrada
        supplier_nation = supplier_ds.merge(
            nation_filt[['n_nationkey']],
            left_on='s_nationkey',
            right_on='n_nationkey',
            how='inner'
        )

        # Filtrar suppliers que estão na lista de qualificados
        result_df = supplier_nation[
            supplier_nation['s_suppkey'].isin(qualified_suppkeys)
        ]

        # Selecionar colunas e ordenar
        result_df = result_df[['s_name', 's_address']].sort_values('s_name')

        return result_df.compute()

    utils.run_query(Q_NUM, query)


if __name__ == "__main__":
    q()
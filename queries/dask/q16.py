from __future__ import annotations

import pandas as pd

from queries.dask import utils

Q_NUM = 16


def q() -> None:
    part_supp_ds = utils.get_part_supp_ds
    part_ds = utils.get_part_ds
    supplier_ds = utils.get_supplier_ds
    
    # first call one time to cache in case we don't include the IO times
    part_supp_ds()
    part_ds()
    supplier_ds()

    def query() -> pd.DataFrame:
        nonlocal part_supp_ds, part_ds, supplier_ds
        
        part_supp_ds = part_supp_ds()
        part_ds = part_ds()
        supplier_ds = supplier_ds()

        # Parâmetros da query
        brand = 'Brand#45'  # :1
        p_type_pattern = 'MEDIUM POLISHED'  # :2
        sizes = [49, 14, 23, 45, 19, 3, 36, 9]  # :3 a :10

        # CORREÇÃO: Identificar suppliers com complaints de forma mais eficiente
        supplier_complaints = supplier_ds[
            supplier_ds['s_comment'].str.contains('Customer.*Complaints', case=False, na=False, regex=True)
        ]['s_suppkey'].compute().tolist()

        # CORREÇÃO: Filtrar partsupp primeiro (mais eficiente)
        partsupp_filtered = part_supp_ds[
            ~part_supp_ds['ps_suppkey'].isin(supplier_complaints)
        ]

        # CORREÇÃO: Juntar partsupp filtrado com part
        table = partsupp_filtered.merge(
            part_ds[['p_partkey', 'p_brand', 'p_type', 'p_size']],
            left_on='ps_partkey',
            right_on='p_partkey',
            how='inner'
        )

        # CORREÇÃO: Aplicar filtros de brand, type e size
        table = table[
            (table['p_brand'] != brand) &
            (~table['p_type'].str.startswith(p_type_pattern)) &
            (table['p_size'].isin(sizes))
        ]

        # CORREÇÃO: Usar nunique() diretamente no groupby (mais eficiente)
        result_df = (
            table.groupby(['p_brand', 'p_type', 'p_size'])
            .ps_suppkey.nunique()
            .reset_index()
            .rename(columns={'ps_suppkey': 'supplier_cnt'})
            .sort_values(
                ['supplier_cnt', 'p_brand', 'p_type', 'p_size'],
                ascending=[False, True, True, True]
            )
        )

        return result_df.compute()

    utils.run_query(Q_NUM, query)


if __name__ == "__main__":
    q()
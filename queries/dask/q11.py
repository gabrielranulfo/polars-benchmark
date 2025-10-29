from __future__ import annotations

import pandas as pd

from queries.dask import utils

Q_NUM = 11


def q() -> None:
    part_supp_ds = utils.get_part_supp_ds
    supplier_ds = utils.get_supplier_ds
    nation_ds = utils.get_nation_ds
    
    # first call one time to cache in case we don't include the IO times
    part_supp_ds()
    supplier_ds()
    nation_ds()

    def query() -> pd.DataFrame:
        nonlocal part_supp_ds, supplier_ds, nation_ds
        
        part_supp_ds = part_supp_ds()
        supplier_ds = supplier_ds()
        nation_ds = nation_ds()

        # Parâmetros da query
        nation_name = 'GERMANY'  # :1
        fraction = 0.0001  # :2

        # Filtrar nation pelo nome
        nation_filt = nation_ds[nation_ds['n_name'] == nation_name]

        # Juntar supplier com nation filtrada
        supplier_nation = supplier_ds.merge(
            nation_filt[['n_nationkey']],
            left_on='s_nationkey',
            right_on='n_nationkey',
            how='inner'
        )

        # Juntar partsupp com supplier (que já tem nation filtrada)
        partsupp_supplier = part_supp_ds.merge(
            supplier_nation[['s_suppkey']],
            left_on='ps_suppkey',
            right_on='s_suppkey',
            how='inner'
        )

        # Calcular value para cada linha
        partsupp_supplier = partsupp_supplier.copy()
        partsupp_supplier['value'] = (
            partsupp_supplier['ps_supplycost'] * partsupp_supplier['ps_availqty']
        )

        # CALCULAR O THRESHOLD (subquery)
        # Calcular o valor total para a nation especificada
        total_value = partsupp_supplier['value'].sum().compute()
        threshold = total_value * fraction

        # Agrupar por ps_partkey e somar os values
        gb = partsupp_supplier.groupby('ps_partkey')
        agg_df = gb.agg(
            value=pd.NamedAgg(column='value', aggfunc='sum')
        ).reset_index()

        # Aplicar filtro HAVING (value > threshold)
        result_df = agg_df[agg_df['value'] > threshold]

        # Ordenar por value descendente
        result_df = result_df.sort_values('value', ascending=False)

        return result_df.compute()

    utils.run_query(Q_NUM, query)


if __name__ == "__main__":
    q()
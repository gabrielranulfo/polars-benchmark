from __future__ import annotations

import pandas as pd

from queries.dask import utils

Q_NUM = 9


def q() -> None:
    line_item_ds = utils.get_line_item_ds
    orders_ds = utils.get_orders_ds
    part_ds = utils.get_part_ds
    supplier_ds = utils.get_supplier_ds
    nation_ds = utils.get_nation_ds
    part_supp_ds = utils.get_part_supp_ds
    
    # first call one time to cache in case we don't include the IO times
    line_item_ds()
    orders_ds()
    part_ds()
    supplier_ds()
    nation_ds()
    part_supp_ds()

    def query() -> pd.DataFrame:
        nonlocal line_item_ds, orders_ds, part_ds, supplier_ds, nation_ds, part_supp_ds
        
        line_item_ds = line_item_ds()
        orders_ds = orders_ds()
        part_ds = part_ds()
        supplier_ds = supplier_ds()
        nation_ds = nation_ds()
        part_supp_ds = part_supp_ds()

        # Parâmetro da query
        part_name_pattern = '%green%'  # :1

        # Filtrar part pelo nome (LIKE pattern)
        part_filt = part_ds[part_ds['p_name'].str.contains('green', case=False, na=False)]

        # Juntar supplier com nation
        supplier_nation = supplier_ds.merge(
            nation_ds[['n_nationkey', 'n_name']],
            left_on='s_nationkey',
            right_on='n_nationkey',
            how='inner'
        ).rename(columns={'n_name': 'nation'})

        # Juntar lineitem com part filtrado
        lineitem_part = line_item_ds.merge(
            part_filt[['p_partkey']],
            left_on='l_partkey',
            right_on='p_partkey',
            how='inner'
        )

        # Juntar lineitem com supplier (que já tem nation)
        lineitem_supplier = lineitem_part.merge(
            supplier_nation[['s_suppkey', 'nation']],
            left_on='l_suppkey',
            right_on='s_suppkey',
            how='inner'
        )

        # Juntar lineitem com partsupp
        lineitem_partsupp = lineitem_supplier.merge(
            part_supp_ds[['ps_partkey', 'ps_suppkey', 'ps_supplycost']],
            left_on=['l_partkey', 'l_suppkey'],
            right_on=['ps_partkey', 'ps_suppkey'],
            how='inner'
        )

        # Juntar lineitem com orders
        lineitem_orders = lineitem_partsupp.merge(
            orders_ds[['o_orderkey', 'o_orderdate']],
            left_on='l_orderkey',
            right_on='o_orderkey',
            how='inner'
        )

        # Criar DataFrame final com cálculos
        final_df = lineitem_orders.copy()
        
        # Extrair ano da orderdate
        final_df['o_year'] = final_df['o_orderdate'].dt.year
        
        # Calcular amount (lucro)
        final_df['amount'] = (
            final_df['l_extendedprice'] * (1 - final_df['l_discount']) - 
            final_df['ps_supplycost'] * final_df['l_quantity']
        )

        # Agrupar por nation e o_year
        gb = final_df.groupby(['nation', 'o_year'])
        agg_df = gb.agg(
            sum_profit=pd.NamedAgg(column='amount', aggfunc='sum')
        ).reset_index()

        # Ordenar por nation e o_year descendente
        result_df = agg_df.sort_values(['nation', 'o_year'], ascending=[True, False])

        return result_df.compute()

    utils.run_query(Q_NUM, query)


if __name__ == "__main__":
    q()
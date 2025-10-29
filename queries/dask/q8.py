from __future__ import annotations

from datetime import date

import pandas as pd

from queries.dask import utils

Q_NUM = 8


def q() -> None:
    line_item_ds = utils.get_line_item_ds
    orders_ds = utils.get_orders_ds
    customer_ds = utils.get_customer_ds
    part_ds = utils.get_part_ds
    supplier_ds = utils.get_supplier_ds
    nation_ds = utils.get_nation_ds
    region_ds = utils.get_region_ds
    
    # first call one time to cache in case we don't include the IO times
    line_item_ds()
    orders_ds()
    customer_ds()
    part_ds()
    supplier_ds()
    nation_ds()
    region_ds()

    def query() -> pd.DataFrame:
        nonlocal line_item_ds, orders_ds, customer_ds, part_ds, supplier_ds, nation_ds, region_ds
        
        line_item_ds = line_item_ds()
        orders_ds = orders_ds()
        customer_ds = customer_ds()
        part_ds = part_ds()
        supplier_ds = supplier_ds()
        nation_ds = nation_ds()
        region_ds = region_ds()

        # Parâmetros da query
        nation_name = 'BRAZIL'  # :1
        region_name = 'AMERICA'  # :2  
        part_type = 'ECONOMY ANODIZED STEEL'  # :3

        start_date = date(1995, 1, 1)
        end_date = date(1996, 12, 31)

        # Filtrar part pela type
        part_filt = part_ds[part_ds['p_type'] == part_type]

        # Filtrar region pelo nome
        region_filt = region_ds[region_ds['r_name'] == region_name]

        # Juntar nation com region filtrada (n1 - nação do cliente)
        nation_customer = nation_ds.merge(
            region_filt, 
            left_on='n_regionkey', 
            right_on='r_regionkey', 
            how='inner'
        )

        # Juntar customer com nation (n1)
        customer_nation = customer_ds.merge(
            nation_customer[['n_nationkey']], 
            left_on='c_nationkey', 
            right_on='n_nationkey', 
            how='inner'
        )

        # CORREÇÃO: Juntar orders com customer filtrado primeiro, depois filtrar por data
        orders_merged = orders_ds.merge(
            customer_nation[['c_custkey']],
            left_on='o_custkey',
            right_on='c_custkey',
            how='inner'
        )
        
        # Agora filtrar usando o DataFrame já mesclado
        orders_filt = orders_merged[
            (orders_merged['o_orderdate'] >= start_date) & 
            (orders_merged['o_orderdate'] <= end_date)
        ]

        # Juntar supplier com nation (n2 - nação do supplier)
        supplier_nation = supplier_ds.merge(
            nation_ds[['n_nationkey', 'n_name']], 
            left_on='s_nationkey', 
            right_on='n_nationkey', 
            how='inner'
        ).rename(columns={'n_name': 's_nation_name'})

        # Juntar lineitem com part filtrado
        lineitem_part = line_item_ds.merge(
            part_filt[['p_partkey']],
            left_on='l_partkey',
            right_on='p_partkey',
            how='inner'
        )

        # Juntar lineitem com supplier (que já tem a nation n2)
        lineitem_supplier = lineitem_part.merge(
            supplier_nation[['s_suppkey', 's_nation_name']],
            left_on='l_suppkey',
            right_on='s_suppkey',
            how='inner'
        )

        # Juntar tudo: lineitem com orders
        final_df = lineitem_supplier.merge(
            orders_filt[['o_orderkey', 'o_orderdate']],
            left_on='l_orderkey',
            right_on='o_orderkey',
            how='inner'
        )

        # Extrair ano da orderdate
        final_df = final_df.copy()
        final_df['o_year'] = final_df['o_orderdate'].dt.year

        # Calcular volume
        final_df['volume'] = final_df['l_extendedprice'] * (1 - final_df['l_discount'])

        # Criar coluna para market share
        final_df['nation_volume'] = final_df.apply(
            lambda x: x['volume'] if x['s_nation_name'] == nation_name else 0,
            axis=1,
            meta=('nation_volume', 'float64')
        )

        # Agrupar por ano e calcular market share
        gb = final_df.groupby('o_year')
        agg_df = gb.agg(
            nation_volume_sum=pd.NamedAgg(column='nation_volume', aggfunc='sum'),
            total_volume_sum=pd.NamedAgg(column='volume', aggfunc='sum')
        ).reset_index()

        # Calcular market share
        agg_df['mkt_share'] = agg_df['nation_volume_sum'] / agg_df['total_volume_sum']

        # Selecionar colunas finais e ordenar
        result_df = agg_df[['o_year', 'mkt_share']].sort_values('o_year')

        return result_df.compute()

    utils.run_query(Q_NUM, query)


if __name__ == "__main__":
    q()
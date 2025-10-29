from __future__ import annotations

import pandas as pd

from queries.dask import utils

Q_NUM = 21


def q() -> None:
    supplier_ds = utils.get_supplier_ds
    line_item_ds = utils.get_line_item_ds
    orders_ds = utils.get_orders_ds
    nation_ds = utils.get_nation_ds
    
    # first call one time to cache in case we don't include the IO times
    supplier_ds()
    line_item_ds()
    orders_ds()
    nation_ds()

    def query() -> pd.DataFrame:
        nonlocal supplier_ds, line_item_ds, orders_ds, nation_ds
        
        supplier_ds = supplier_ds()
        line_item_ds = line_item_ds()
        orders_ds = orders_ds()
        nation_ds = nation_ds()

        # Parâmetro da query
        nation_name = 'SAUDI ARABIA'  # :1

        # Filtrar nation pelo nome
        nation_filt = nation_ds[nation_ds['n_name'] == nation_name]

        # Juntar supplier com nation
        supplier_nation = supplier_ds.merge(
            nation_filt[['n_nationkey']],
            left_on='s_nationkey',
            right_on='n_nationkey',
            how='inner'
        )

        # Filtrar orders por status 'F'
        orders_filt = orders_ds[orders_ds['o_orderstatus'] == 'F']

        # Juntar lineitem com orders filtrados
        lineitem_orders = line_item_ds.merge(
            orders_filt[['o_orderkey']],
            left_on='l_orderkey',
            right_on='o_orderkey',
            how='inner'
        )

        # Filtrar lineitems com receiptdate > commitdate (atrasados)
        late_lineitems = lineitem_orders[
            lineitem_orders['l_receiptdate'] > lineitem_orders['l_commitdate']
        ]

        # Juntar com supplier
        late_lineitems_supplier = late_lineitems.merge(
            supplier_nation[['s_suppkey', 's_name']],
            left_on='l_suppkey',
            right_on='s_suppkey',
            how='inner'
        )

        # Primeira EXISTS: orders com múltiplos suppliers
        # Contar suppliers distintos por order
        order_supplier_count = line_item_ds.groupby('l_orderkey')['l_suppkey'].nunique()
        order_supplier_count = order_supplier_count.reset_index()
        order_supplier_count = order_supplier_count.rename(columns={'l_suppkey': 'supplier_count'})
        
        orders_multiple_suppliers = order_supplier_count[order_supplier_count['supplier_count'] > 1]
        orders_multiple_keys = orders_multiple_suppliers['l_orderkey'].compute().tolist()

        # Filtrar late_lineitems para orders com múltiplos suppliers
        late_multi_supplier = late_lineitems_supplier[
            late_lineitems_supplier['l_orderkey'].isin(orders_multiple_keys)
        ]

        # CORREÇÃO: Abordagem eficiente para NOT EXISTS
        # Contar quantos suppliers atrasados existem por order
        late_suppliers_by_order = line_item_ds[
            line_item_ds['l_receiptdate'] > line_item_ds['l_commitdate']
        ].groupby('l_orderkey')['l_suppkey'].nunique()
        
        late_suppliers_by_order = late_suppliers_by_order.reset_index()
        late_suppliers_by_order = late_suppliers_by_order.rename(columns={'l_suppkey': 'late_supplier_count'})

        # Juntar esta contagem com nossos candidatos
        late_multi_supplier_with_count = late_multi_supplier.merge(
            late_suppliers_by_order,
            left_on='l_orderkey',
            right_on='l_orderkey',
            how='left'
        )

        # Preencher NaN com 0 (casos onde não há contagem)
        late_multi_supplier_with_count['late_supplier_count'] = late_multi_supplier_with_count['late_supplier_count'].fillna(0)

        # CORREÇÃO: Um supplier é o único atrasado se late_supplier_count = 1
        final_suppliers = late_multi_supplier_with_count[
            late_multi_supplier_with_count['late_supplier_count'] == 1
        ]

        # Agrupar por supplier name e contar
        result_df = final_suppliers.groupby('s_name').size()
        result_df = result_df.reset_index()
        result_df = result_df.rename(columns={0: 'numwait'})

        # Ordenar por numwait descendente, s_name ascendente
        result_df = result_df.sort_values(['numwait', 's_name'], ascending=[False, True])

        return result_df.compute()

    utils.run_query(Q_NUM, query)


if __name__ == "__main__":
    q()
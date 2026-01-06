import duckdb
from pathlib import Path

from queries.duckdb import utils

Q_NUM = 15


def q() -> None:
    supplier_ds = utils.get_supplier_ds()
    line_item_ds = utils.get_line_item_ds()

    query_str = f'''
select
    s_suppkey,
    s_name,
    s_address,
    s_phone,
    sum(l_extendedprice * (1 - l_discount)) as total_revenue
from
    {supplier_ds},
    {line_item_ds}
where
    s_suppkey = l_suppkey
    and l_shipdate >= date '1996-01-01'
    and l_shipdate < date '1996-01-01' + interval '3' month
group by
    s_suppkey,
    s_name,
    s_address,
    s_phone
order by
    total_revenue desc;
'''

    q_final = duckdb.sql(query_str)
    utils.run_query(Q_NUM, q_final)


if __name__ == "__main__":
    q()

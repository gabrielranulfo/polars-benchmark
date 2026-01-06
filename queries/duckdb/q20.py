import duckdb
from pathlib import Path

from queries.duckdb import utils

Q_NUM = 20


def q() -> None:
    supplier_ds = utils.get_supplier_ds()
    nation_ds = utils.get_nation_ds()
    partsupp_ds = utils.get_part_supp_ds()
    line_item_ds = utils.get_line_item_ds()
    part_ds = utils.get_part_ds()

    query_str = f'''
-- Q20 inline
select
    s_name,
    s_address
from
    {supplier_ds},
    {nation_ds},
    {partsupp_ds},
    (
        select
            l_partkey,
            l_suppkey,
            0.5 * sum(l_quantity) as half_qty
        from
            {line_item_ds}
        where
            l_shipdate >= date '1994-01-01'
            and l_shipdate < date '1994-01-01' + interval '1' year
        group by
            l_partkey,
            l_suppkey
    ) as li
where
    {partsupp_ds}.ps_partkey in (
        select p_partkey from {part_ds} where p_name like 'forest%'
    )
    and {partsupp_ds}.ps_partkey = li.l_partkey
    and {partsupp_ds}.ps_suppkey = li.l_suppkey
    and {partsupp_ds}.ps_availqty > li.half_qty
    and {partsupp_ds}.ps_suppkey = {supplier_ds}.s_suppkey
    and {supplier_ds}.s_nationkey = {nation_ds}.n_nationkey
    and {nation_ds}.n_name = 'CANADA'
order by
    s_name;
'''

    q_final = duckdb.sql(query_str)
    utils.run_query(Q_NUM, q_final)


if __name__ == "__main__":
    q()

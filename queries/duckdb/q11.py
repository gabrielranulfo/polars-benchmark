import duckdb
from pathlib import Path

from queries.duckdb import utils

Q_NUM = 11


def q() -> None:
    partsupp_ds = utils.get_part_supp_ds()
    supplier_ds = utils.get_supplier_ds()
    nation_ds = utils.get_nation_ds()

    query_str = f'''
select
    ps_partkey,
    sum(ps_supplycost * ps_availqty) as value
from
    {partsupp_ds},
    {supplier_ds},
    {nation_ds}
where
    {partsupp_ds}.ps_suppkey = {supplier_ds}.s_suppkey
    and {supplier_ds}.s_nationkey = {nation_ds}.n_nationkey
    and {nation_ds}.n_name = 'GERMANY'
group by
    ps_partkey
having
    sum(ps_supplycost * ps_availqty) > (
        select
            sum(ps_supplycost * ps_availqty) * 0.0001
        from
            {partsupp_ds}
            join {supplier_ds} on {partsupp_ds}.ps_suppkey = {supplier_ds}.s_suppkey
            join {nation_ds} on {supplier_ds}.s_nationkey = {nation_ds}.n_nationkey
        where
            {nation_ds}.n_name = 'GERMANY'
    )
order by
    value desc;
'''

    q_final = duckdb.sql(query_str)
    utils.run_query(Q_NUM, q_final)


if __name__ == "__main__":
    q()

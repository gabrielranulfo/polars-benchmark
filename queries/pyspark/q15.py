from queries.pyspark import utils

Q_NUM = 15


def q() -> None:
    # Primeiro criar a view
    create_view_str = """
    create or replace temporary view revenue as
    select
        l_suppkey as supplier_no,
        sum(l_extendedprice * (1 - l_discount)) as total_revenue
    from
        lineitem
    where
        l_shipdate >= date '1996-01-01'
        and l_shipdate < date '1996-01-01' + interval '3' month
    group by
        l_suppkey
    """
    
    # Query principal
    query_str = """
    select
        s_suppkey,
        s_name,
        s_address,
        s_phone,
        total_revenue
    from
        supplier,
        revenue
    where
        s_suppkey = supplier_no
        and total_revenue = (
            select
                max(total_revenue)
            from
                revenue
        )
    order by
        s_suppkey
    """

    utils.get_line_item_ds()
    utils.get_supplier_ds()

    spark = utils.get_or_create_spark()
    
    # Criar a view primeiro
    spark.sql(create_view_str)
    
    # Executar a query principal
    q_final = spark.sql(query_str)

    utils.run_query(Q_NUM, q_final)


if __name__ == "__main__":
    q()
import polars as pl

from queries.polars import utils

Q_NUM = 18


def q() -> None:
    customer = utils.get_customer_ds()
    orders = utils.get_orders_ds()
    lineitem = utils.get_line_item_ds()

    var1 = 300

    # Encontra orderkeys com quantidade total > var1
    large_orders = (
        lineitem.group_by("l_orderkey")
        .agg(pl.sum("l_quantity").alias("total_qty"))
        .filter(pl.col("total_qty") > var1)
        .select("l_orderkey")
    )

    q_final = (
        customer.join(orders, left_on="c_custkey", right_on="o_custkey")
        .join(large_orders, left_on="o_orderkey", right_on="l_orderkey", how="semi")
        .join(lineitem, left_on="o_orderkey", right_on="l_orderkey")
        .group_by("c_name", "c_custkey", "o_orderkey", "o_orderdate", "o_totalprice")
        .agg(pl.sum("l_quantity"))
        .sort(by=["o_totalprice", "o_orderdate"], descending=[True, False])
        .head(100)
    )

    utils.run_query(Q_NUM, q_final)


if __name__ == "__main__":
    q()


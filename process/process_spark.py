from pyspark.sql import DataFrame
from pyspark.sql.functions import to_date, col, lag, log, sum, when, greatest, least, abs, round as spark_round


def spark_preProcessTradePrice(df: DataFrame, decimal_places: int = 4):
    """
    Pre-process data from trade_price table, handling multiple Decimal price fields.
    Rounds the calculated fields to the specified number of decimal places.
    
    :param df: Input DataFrame
    :param decimal_places: Number of decimal places to round to (default: 4)
    :return: Processed DataFrame
    """
    processed_df = (df
        .withColumn("trade_time", to_date("trade_time"))
        .dropDuplicates(["code", "trade_time", "candle"])
        # .withColumn("daily_range", 
        #     spark_round(abs(greatest(col("high") - col("low"), col("close") - col("open"))), decimal_places)
        # )
        .orderBy("code", "trade_time")
    )
    
    return processed_df
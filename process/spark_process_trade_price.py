from pyspark.sql import DataFrame
from pyspark.sql.functions import col, min, max, to_timestamp, date_format
from pyspark.sql.window import Window

def trade_price_post_process(df: DataFrame) -> DataFrame:
    """
    处理 Spark DataFrame 并返回分组后的数据列表
    
    Args:
        df (DataFrame): 输入的 Spark DataFrame
    
    Returns:
        List[Tuple[DataFrame, str]]: 包含分组后的 DataFrame 和对应文件名的列表
    """
    # 处理时间列
    df = df.withColumn("trade_time_date", col("trade_time").cast("date"))
    df = df.withColumn("trade_time",
        to_timestamp(
            date_format(col("trade_time"), "yyyy-MM-dd HH:mm:ss.SSSSSS"),
            "yyyy-MM-dd HH:mm:ss.SSSSSS"
        )
    )
    
    # 使用窗口函数获取每个组的最早和最晚日期
    window = Window.partitionBy("code", "candle")
    df =  df.withColumn("start_date", min(col("trade_time_date")).over(window)) \
                      .withColumn("end_date", max(col("trade_time_date")).over(window))
    
    return df
    

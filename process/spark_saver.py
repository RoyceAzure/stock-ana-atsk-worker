from pyspark.sql import DataFrame
from pyspark.sql.functions import col, min, max, to_timestamp, date_format
from pyspark.sql.window import Window
import pandas as pd
from abc import ABC, abstractmethod
import os

def group_and_process_data(df: DataFrame):
    """按 (code, candle) 分组处理数据"""
    grouped = df.groupBy("code", "candle")
    # 这里可以添加任何额外的聚合操作
    return grouped.agg({})  # 目前没有聚合，返回所有列

class DataStorage(ABC):
    @abstractmethod
    def save(self, df: pd.DataFrame, path : str, filename: str):
        pass

class ExcelStorage(DataStorage):
    def save(self, df: pd.DataFrame, filename: str):
        df.to_excel(filename, index=True)
        print(f"Data saved to {filename}")


def save_grouped_data(spark_df: DataFrame, storage: DataStorage, base_path: str):
    # 获取所有唯一的 (code, candle) 组合
    groups = spark_df.select("code", "candle").distinct().collect()
    
    for row in groups:
        code, candle = row['code'], row['candle']
        
        # 过滤当前组的数据
        group_data = spark_df.filter((col("code") == code) & (col("candle") == candle))
        
        # 转换为 Pandas DataFrame
        pandas_df = group_data.toPandas()
        
        # 创建文件名
        filename = os.path.join(base_path, f"{code}_{candle}.xlsx")
        
        # 保存数据
        storage.save(pandas_df, filename)
        
        

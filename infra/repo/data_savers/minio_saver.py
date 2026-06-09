from io import BytesIO
import json
import logging
from typing import Any, BinaryIO, Optional, Tuple, Union
from .base import DataSaver
from pandas import DataFrame
from infra.repo.minio_dao import MinioConfig, conn_minio

class MinioSaver(DataSaver):
    """MinIO 數據保存器
    這個類用於將各種類型的數據保存到 MinIO 對象存儲中。
    支持多種數據類型的保存，包括 DataFrame、二進制數據和 JSON 數據。
    
    主要特點：
    - 支持多種數據格式的保存
    - 提供日誌記錄功能
    - 支持文件追加操作
    - 自動處理數據類型轉換
    Attributes:
        saver_type (str): 保存器類型標識
        dao: MinIO 客戶端連接對象
        logger: 日誌記錄器
    """
    def __init__(self, config : MinioConfig):

        self.saver_type = "minio"
        #不使用DI  方便管理生命週期
        self.dao = conn_minio(config)
        self._setup_logging()
        
        
    def _setup_logging(self):
        self.logger = logging.getLogger(f'minio saver')
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
        
    def save_file(self, full_path: str, data: Union[BinaryIO, bytes, DataFrame], is_trade_result : bool = False) -> Tuple[Optional[Any], Optional[str]]:
        try:
            if isinstance(data, DataFrame):
                #沒有交易資料  寫入預設欄位
                if data.empty and is_trade_result:
                    data = DataFrame(columns=DataSaver.trade_result_default_column)
                    
                # 直接將DataFrame轉換為CSV字串
                csv_data = data.to_csv(index=False)
                # 將CSV字串轉換為bytes
                buffer = BytesIO(csv_data.encode('utf-8'))
                content_type = "text/csv"
            elif isinstance(data, bytes):
                buffer = BytesIO(data)
                content_type = "application/octet-stream"
            elif hasattr(data, 'read'):
                buffer = BytesIO(data.read())
                content_type = "application/octet-stream"
            else:
                return None, f"Unsupported data type: {type(data)}"
            
            # 確認buffer中有數據
            buffer.seek(0)
            data_size = buffer.getbuffer().nbytes
            if data_size == 0:
                return None, "Buffer is empty"
                
            path_split = full_path.split("/", 1)
            bucket = path_split[0]
            file_path = path_split[1]
            
            # 寫入minio
            self.dao.put_object(
                bucket,
                file_path,
                buffer,
                length=data_size,  # 使用實際的數據大小
                content_type=content_type
            )
            
            return True, None
        
        except Exception as e:
            return None, str(e)

    def as_dict(self) -> dict:
        return {
            "saver_name" : self.__class__.__name__,
        }
        
    def append_to_file(self, full_path: str, data: dict) -> Tuple[Optional[Any], Optional[str]]:
        try:
            existing_data = {}
            path_split = full_path.split("/", 1)
            bucket = path_split[0]
            file_path = path_split[1]
            try:
                response = self.dao.get_object(bucket, file_path)
                existing_data = json.loads(response.read().decode('utf-8'))
            except:
                pass
            
            existing_data.update(data)
            
            # 轉換為 bytes 並寫入
            json_bytes = json.dumps(existing_data, indent=2).encode('utf-8')
            buffer = BytesIO(json_bytes)
            
            # 上傳到 MinIO
            self.dao.put_object(
                bucket,
                file_path,
                buffer,
                length=len(json_bytes),
                content_type="application/json"
            )
            
            return True, None
            
        except Exception as e:
            return None, str(e)

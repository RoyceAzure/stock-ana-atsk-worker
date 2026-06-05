from dataclasses import dataclass
from infra.repo import Minio
from core.config.config import Config

@dataclass
class MinioConfig:
    host : str = Config().MINIO_HOST
    access_key : str = Config().MINIO_ROOT_USER
    secret_key : str = Config().MINIO_ROOT_PASSWORD
    port:int = Config().MINIO_PORT
    region:str = Config().AWS_REGION
    
    def as_dict(self):
        return self.__dict__
        
def conn_minio(minio_config : MinioConfig) -> Minio:
    """
    創建到 PostgreSQL 數據庫的連接。
    
    :param host: 數據庫服務器地址
    :param database: 數據庫名稱
    :param user: 用戶名
    :param password: 密碼
    :param port: 端口號，默認為 5432
    :return: 如果連接成功，返回連接對象；否則返回 None
    """
    return Minio(
            f"{minio_config.host}:{minio_config.port}",
            access_key=minio_config.access_key,
            secret_key=minio_config.secret_key,
            secure=True
        )
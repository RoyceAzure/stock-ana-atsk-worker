from abc import ABC, abstractmethod
from typing import Any, List, Tuple, Optional

class DataLoader(ABC):
    @abstractmethod
    def query_data(self, **kwargs: Any) -> Tuple[Optional[Any], Optional[str]]:
        """
        查詢數據的抽象方法。

        :param kwargs: 可變關鍵字參數，允許傳入任意命名參數。
        :return: 查詢結果，類型取決於具體實現。
        """
        pass
    
    @abstractmethod
    def query_datas(self, **kwargs: Any) -> Tuple[Optional[List[Any]], Optional[str]]:
        """
        查詢數據的抽象方法。

        :param kwargs: 可變關鍵字參數，允許傳入任意命名參數。
        :return: 查詢結果，類型取決於具體實現。
        """
        pass
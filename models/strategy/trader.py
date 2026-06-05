import pandas as pd
from models.strategy.base import TradeAction

class Trade:
    def __init__(self, row, profit_factor, loss_factor):
        """
        初始化交易對象
        """
        try:
            self.running = True
            self.start_index = row.name
            
            # 確保因子是 Decimal 類型
            self.profit_factor = profit_factor
            self.loss_factor = loss_factor
            
            # 確保價格相關的值都是 Decimal 類型
            self.start_price = row.open
            self.TP = row.TP
            self.SL = row.SL
            
            # 非數值型別的屬性
            self.start_time = row.trade_time
            self.SIGNAL = row.SIGNAL
            
            # 初始化其他可能會用到的屬性
            self.close_index = None
            self.end_time = None
            self.close_price = None
            self.total_return = None
            self.total_return_rate = None
            
        except Exception as e:
            raise

    def close_trade(self, row, close_price, is_force_closed: bool = False):
        """關閉交易"""
        try:
            if not is_force_closed:
                self.running = False
            self.close_index = row.name
            self.end_time = row.trade_time
            self.close_price = close_price
            # 計算收益
            self.total_return = self.close_price - self.start_price
            # 避免除以零
            if self.start_price == 0.0:
                self.total_return_rate = 0.0
            else:
                self.total_return_rate = self.total_return / self.start_price
                
        except Exception as e:
            raise

    def update(self, row):
        """更新交易狀態"""
        try:
            if self.running and row.SIGNAL == TradeAction.SELL.value:
                # 確保比較值是 Decimal
                high = row.high
                low = row.low
                
                if high >= self.TP:
                    self.close_trade(row, high)
                elif low <= self.SL:
                    self.close_trade(row, low)
                    
        except Exception as e:
            raise

    def to_dataframe(self):
        """轉換為 DataFrame"""
        try:
            data = {
                'start_index': self.start_index,
                'close_index': self.close_index,
                'start_time': self.start_time,
                'end_time': self.end_time,
                'start_price': float(self.start_price) if self.start_price else None,
                'TP': float(self.TP) if self.TP else None,
                'SL': float(self.SL) if self.SL else None,
                'close_price': float(self.close_price) if self.close_price else None,
                'total_return': float(self.total_return) if self.total_return else None,
                'total_return_rate': float(self.total_return_rate) if self.total_return_rate else None,
                'status': "open" if self.running else "close"
            }
            return pd.DataFrame([data])
            
        except Exception as e:
            raise
    
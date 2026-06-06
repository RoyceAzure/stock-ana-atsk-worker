from typing import Dict, List, Union
import pandas as pd
from abc import ABC, abstractmethod
from pydantic import Field
from models.basemodel import BaseModelWithConfig
from util.process import ewm

class IndicatorInfo(BaseModelWithConfig):
    """
    "name" : "EMA", 指標統一名稱
    "display_name": 該指標在測試結果 dataframe裡的所有相關欄位名稱
    "params":{
        "key" : "value",
    }
    """
    name: str = Field(description="指標統一名稱")
    display_name: List[str] = Field(description="該指標在測試結果 dataframe裡的欄位名稱")
    params: Dict[str, Union[int, float]] = Field(description="指標參數")

    def as_dict(self) -> dict:
        """轉換為字典格式"""
        return self.model_dump()


class Indicator(ABC):
    @abstractmethod
    def apply(self, df : pd.DataFrame) -> pd.DataFrame:
        pass
    
    def describe(self) -> str:
        pass
    
    def get_info(self) -> IndicatorInfo:
        pass

class BollingerBands(Indicator):
    def __init__(self, n : int =20, s : int =2):
        """
        Args:
            n (int) : 時間週期
            s : 表準差增幅
        """
        self.n = n
        self.s = s
        self.info = IndicatorInfo(
                name="BollingerBands", 
                display_name=[
                    "BB_MA",
                    "BB_UP",
                    "BB_LW"
                ],
                params={
                "n" : self.n,
                "s" : self.s
            }
        )
    
    def apply(self, df : pd.DataFrame) -> pd.DataFrame:
        """
        基于一定周期内的简单移动平均线（SMA）和标准差
        由三条线组成的价格波动区间指标，包括中轨、上轨和下轨

        使用典型價格計算BollingerBands，非close
        直接將結果apply到df

        """
        df_ana = df.copy()
        typical_p = (df_ana.close + df_ana.high + df_ana.low)/3
        stddev = typical_p.rolling(window=self.n).std()
        df_ana[f"BB_MA"] = typical_p.rolling(window=self.n).mean()
        df_ana[f"BB_UP"] = df_ana[f"BB_MA"] + stddev*self.s 
        df_ana[f"BB_LW"] = df_ana[f"BB_MA"] - stddev*self.s
        return df_ana
    
    def get_info(self):
        return self.info
    
    def describe(self)-> str:
        info = self.get_info()
        
        param_descriptions = []
        param_str = ", ".join(f"{k}: {v}" for k, v in info.params.items())
        param_descriptions.append(param_str)
        
        return f"""
        指標說明:
                價格經常在上下軌之間波動，並有回歸中間帶的趨勢。
                當價格從帶的邊緣向中間移動時，可能預示著趨勢反轉。
                在強勁上升趨勢中，價格經常貼近或略微超出上軌運行。
                當價格接近或突破上軌時，可能表示市場處於超買狀態。
                當價格接近或突破下軌時，可能表示市場處於超賣狀態。
                上下兩條之間的距離反映了市場的波動性。
                當兩條帶擴張時，表示市場波動性增加；當收縮時，表示波動性減少。
        
        參數配置:
        {chr(10).join('  • ' + desc for desc in param_descriptions)}
        """

class ATR(Indicator):
    def __init__(self, n : int = 14):
        """
        Args:
            n (int) : 時間週期
        """
        self.n = n
        self.display_name = f"ATR_{self.n}"
        self.info = IndicatorInfo(
                name="ATR", 
                display_name=[self.display_name],
                params={
                    "period" : self.n,
                }
        )
        
    def apply(self, df : pd.DataFrame) -> pd.DataFrame:
        """
        基于一定周期内的真实范围（True Range，TR）的平均值
        一个反映市场波动性的指标，不表示价格方向，只表示波动幅度
        
        真實範圍（True Range, TR）的計算：
        TR 是以下三個值中的最大者：

        當日最高價與最低價之差
        當日最高價與前一日收盤價之差的絕對值
        前一日收盤價與當日最低價之差的絕對值

        衡量市場波動性：ATR 值越高，表示市場波動越大。
        設置止損：交易者可能使用 ATR 的倍數來設置止損點。
        判斷趨勢強度：ATR 上升可能表示趨勢正在增強。
        識別潛在的突破：ATR 突然增大可能預示價格突破。
        
        ATR 是一個滯後指標，因為它基於歷史數據。
        ATR 不顯示價格方向，只反映波動幅度。
        通常與其他技術指標結合使用，以提供更全面的市場分析。

        """
        df_ana = df.copy()
        prev_c = df_ana.close.shift(1)
        tr1 = df_ana.high - df_ana.low
        tr2 = abs(df_ana.high - prev_c)
        tr3 = abs(prev_c - df_ana.low)

        tr = pd.DataFrame({"tr1" : tr1, "tr2" : tr2, "tr3": tr3}).max(axis=1)

        #使用簡單平均移動計算  此處算完ATR會是 float64
        df_ana[self.display_name] = tr.rolling(window=self.n).mean()



        return df_ana
    
    def get_info(self):
        return self.info 
    
    def describe(self)-> str:
        info = self.get_info()
        
        param_descriptions = []
        param_str = ", ".join(f"{k}: {v}" for k, v in info.params.items())
        param_descriptions.append(param_str)
        
        return f"""
        指標說明:
            基于一定周期内的真实范围（True Range，TR）的平均值
            一个反映市场波动性的指标，不表示价格方向，只表示波动幅度

            真實範圍（True Range, TR）的計算：
            TR 是以下三個值中的最大者：

            當日最高價與最低價之差
            當日最高價與前一日收盤價之差的絕對值
            前一日收盤價與當日最低價之差的絕對值

            衡量市場波動性：ATR 值越高，表示市場波動越大。
            設置止損：交易者可能使用 ATR 的倍數來設置止損點。
            判斷趨勢強度：ATR 上升可能表示趨勢正在增強。
            識別潛在的突破：ATR 突然增大可能預示價格突破。

            ATR 是一個滯後指標，因為它基於歷史數據。
            ATR 不顯示價格方向，只反映波動幅度。
            通常與其他技術指標結合使用，以提供更全面的市場分析。
        
        參數配置:
        {chr(10).join('  • ' + desc for desc in param_descriptions)}
        """

class KeltnerChannels(Indicator):
    def __init__(self, n_ema :int = 20, n_atr :int= 10):
        """
        Args:
            n_ema (int) : 計算ema的時間週期
            n_atr (int) : 計算atr的時間週期
        """
        self.n_ema = n_ema
        self.n_atr = n_atr
        self.atr_indicator = ATR(self.n_atr)
        self.ema_indicator = EMA(self.n_ema)
    
        self.info = IndicatorInfo(
                name="KeltnerChannels", 
                display_name=["KeUp","KeLo"],
                params={
                    "ema_period" : self.n_ema,
                    "atr_period" : self.n_atr   
                }
        )
    
    def apply(self, df : pd.DataFrame) -> pd.DataFrame:
        df_ana = df.copy()

        df_ana = self.ema_indicator.apply(df_ana)
        df_ana = self.atr_indicator.apply(df_ana)


        df_ana[f"KeUp"] = df_ana[self.atr_indicator.display_name]*2 + df_ana[self.ema_indicator.display_name]
        df_ana[f"KeLo"] = df_ana[self.ema_indicator.display_name] - 2* df_ana[self.atr_indicator.display_name]
        return df_ana
    
    def get_info(self):
        return self.info

    
    def describe(self)-> str:
        info = self.get_info()
        
        param_descriptions = []
        param_str = ", ".join(f"{k}: {v}" for k, v in info.params.items())
        param_descriptions.append(param_str)
        
        return f"""
        指標說明:
        基于一定周期内的平均价格（通常是指数移动平均线EMA）和平均真实范围（ATR）
        由三条线组成的价格波动区间指标，包括中心线、上轨和下轨

        識別趨勢：

        當價格持續在上通道線之上移動時，可能表示強勁的上升趨勢。
        當價格持續在下通道線之下移動時，可能表示強勁的下降趨勢。
        當價格在通道內波動時，可能表示橫盤整理。


        判斷超買超賣：

        當價格觸及或突破上通道線時，可能表示市場超買，潛在的回調機會。
        當價格觸及或突破下通道線時，可能表示市場超賣，潛在的反彈機會。


        預測價格波動：

        通道的寬度反映了市場的波動性。通道變寬表示波動性增加，變窄則表示波動性減少。


        提供交易信號：

        一些交易者在價格從通道外回到通道內時進行交易。
        也有人在價格突破通道時尋找交易機會，預期更大幅度的移動。


        支撐和阻力水平：

        上下通道線可以作為動態的支撐和阻力水平。


        與其他指標配合：

        Keltner Channels 常與其他技術指標（如 RSI、MACD 等）結合使用，以確認交易信號。

        EMA:
        為每個數據點分配一個權重，這個權重隨時間指數衰減。最新的數據點獲得最高的權重，而較早的數據點獲得較低的權重
        EMA_t = α * price_t + (1 - α) * EMA_(t-1)
        α = 2 / (span + 1)
        平滑因子 α：

        α 通常设置为 2 / (N + 1)，其中 N 是周期数
        较大的 α 值会使 EWMA 对新数据更敏感 => 週期越長 數據越不敏感
        较小的 α 值会产生更平滑的结果 => 週期越小  數據越敏感
        
        參數配置:
        {chr(10).join('  • ' + desc for desc in param_descriptions)}
        """

class RSI(Indicator):
    def __init__(self, n :int= 14):
        """
        Args:
            n (int): rsi 週期
        """
        self.n = n
        self.display_name = f"RSI_{self.n}"
        self.info = IndicatorInfo(
                name="RSI", 
                display_name=[self.display_name],
                params={
                    "period" : self.n
                }
        )
    
    def apply(self, df : pd.DataFrame) -> pd.DataFrame:
        df_ana = df.copy()
            
        # 1. 計算價差 (Current Close - Previous Close)
        # gains 包含正值(漲)與負值(跌)
        gains = df_ana.close.diff()
        
        # 2. 分離漲跌幅 (向量化處理，保留原始 Index 避免 NaN)
        # clip(lower=0): 負值轉為 0，只留漲幅
        # clip(upper=0): 正值轉為 0，只留跌幅(取負號轉正值)
        win = gains.clip(lower=0)
        loss = -gains.clip(upper=0)

        # 3. 計算 RMA (Wilder's Smoothing)
        # RSI 標準算法使用 alpha = 1/n，且不調整權重 (adjust=False)
        # min_periods 確保在資料量不足時不輸出錯誤指標
        alpha = 1 / self.n
        win_rma = win.ewm(alpha=alpha, min_periods=self.n, adjust=False).mean()
        loss_rma = loss.ewm(alpha=alpha, min_periods=self.n, adjust=False).mean()

        # 4. 計算相對強度 RS (Relative Strength)
        rs = win_rma / loss_rma
        
        # 5. 轉換為 0~100 的 RSI 指標並四捨五入
        # 公式：100 - (100 / (1 + RS))
        df_ana[self.display_name] = (100 - (100 / (1 + rs))).round(2)
        
        return df_ana
    
    def get_info(self):
        return self.info
    
    def describe(self)-> str:
        info = self.get_info()
        
        param_descriptions = []
        param_str = ", ".join(f"{k}: {v}" for k, v in info.params.items())
        param_descriptions.append(param_str)
        
            
        return f"""
        指標說明:
            一定時間價格上漲與下跌的比值
            其他常见周期：

                5天：非常短期，反应迅速但可能产生更多假信号。
                7天：介于5天和14天之间的折中选择。
                30天：用于更长期的市场趋势分析。    


                RSI的解读：
                就是一定周期内平均上涨和平均下跌的比值  用來看上漲和下跌的相對強度

                RSI > 70 通常被认为是超买状态，可能预示价格回落
                RSI < 30 通常被认为是超卖状态，可能预示价格反弹
                50左右的RSI值表示市场处于中性状态


                （RS）：
                RS = 平均涨幅 / 平均跌幅
                RSI = 100 - (100 / (1 + RS))

        
        參數配置:
        {chr(10).join('  • ' + desc for desc in param_descriptions)}
        """

class MACD(Indicator):
    def __init__(self,  n_slow :int= 26, n_fast : int= 12, n_signal : int =9):
        """
        Args:
            n_ema (int) : 計算ema的時間週期
            n_atr (int) : 計算atr的時間週期
        """
        self.n_slow = n_slow
        self.n_fast = n_fast
        self.n_signal = n_signal
        self.info = IndicatorInfo(
                name="MACD", 
                display_name=["MACD","MACD_SIGNAL", "HIST"],
                params={
                "slow_period" : self.n_slow,
                "fast_period" : self.n_fast,
                "signal_period" : self.n_signal  
            }
        )
            
    
    def apply(self, df : pd.DataFrame) -> pd.DataFrame:
        df_ana = df.copy()
        
        ema_long = ewm(df_ana.close, min_periods = self.n_slow, span=self.n_slow)
        ema_short = ewm(df_ana.close, min_periods = self.n_fast, span=self.n_fast)

        df_ana["MACD"] = ema_short - ema_long
        df_ana["MACD_SIGNAL"] = ewm(df_ana["MACD"], min_periods = self.n_signal, span = self.n_signal)
        df_ana["HIST"] = df_ana["MACD"] - df_ana["MACD_SIGNAL"]

        return df_ana
    
    def get_info(self):
        return self.info
    
    def describe(self)-> str:
        info = self.get_info()
        
        param_descriptions = []
        param_str = ", ".join(f"{k}: {v}" for k, v in info.params.items())
        param_descriptions.append(param_str)
        
            
        return f"""
        指標說明:
            MACD (Moving Average Convergence Divergence) 移動平均匯聚背離指標
            通過比較兩條移動平均線的差值來判斷市場趨勢和動能
            
        計算方法：
            1. 差離值（DIF）：
            - 計算快速EMA與慢速EMA的差值
            - DIF = 快速EMA - 慢速EMA
            
            2. 信號線（Signal）：
            - 對DIF進行移動平均
            - Signal = DIF的N日EMA
            
            3. MACD柱狀圖（Histogram）：
            - DIF與信號線的差值
            - Histogram = DIF - Signal
        
        常用參數設定：
            快速EMA：12日
            慢速EMA：26日
            信號線：9日
            
        買賣信號：
            1. 黃金交叉：DIF從下方突破Signal，為買入信號
            2. 死亡交叉：DIF從上方跌破Signal，為賣出信號
            3. 柱狀圖：
            - 由負轉正，市場轉為看漲
            - 由正轉負，市場轉為看跌
            
        背離信號：
            1. 頂背離（賣出）：
            - 價格創新高，但MACD未創新高
            - 表示上漲動能減弱，可能反轉向下
            
            2. 底背離（買入）：
            - 價格創新低，但MACD未創新低
            - 表示下跌動能減弱，可能反轉向上
        
        使用注意：
            1. MACD為滯後指標，信號會較價格變化慢
            2. 建議搭配其他技術指標或分析方法使用
            3. 在橫盤整理時可能產生假信號
            4. 背離信號的可信度通常高於一般交叉信號
            
        參數配置:
        {chr(10).join('  • ' + desc for desc in param_descriptions)}
        """
        
        
class EMA(Indicator):
    def __init__(self,  n_ema = 10):
        """
        使用ema計算移動平均 產生的欄位統稱MA
        Args:
            n_ema (int) : 計算ema的時間週期
        """
        self.n_ema = n_ema
        self.display_name = f"EMA_{self.n_ema}"
        self.info = IndicatorInfo(
            name="EMA", 
            display_name=[self.display_name],
            params={"period" : self.n_ema}
        )
        
    def apply(self, df : pd.DataFrame) -> pd.DataFrame:
        df_ana = df.copy()
        
        df_ana[self.display_name] = ewm(df_ana.close, min_periods = self.n_ema, span=self.n_ema)

        return df_ana
    
    def get_info(self) -> IndicatorInfo:
        return self.info
    
    def describe(self)-> str:
        info = self.get_info()
        
        param_descriptions = []
        param_str = ", ".join(f"{k}: {v}" for k, v in info.params.items())
        param_descriptions.append(param_str)
        
        # 使用更美观的多行格式
        description = f"""📊 指標說明: 移動平均線 (Moving Average)

        參數配置:
        {chr(10).join('  • ' + desc for desc in param_descriptions)}

        特點:
        • 追蹤價格趨勢
        • 平滑短期波動
        • 提供技術分析支持
        """
        return description


class MA(Indicator):
    def __init__(self, n_ma = 10):
        """
        使用簡單移動平均線(SMA)計算移動平均
        Args:
            n_ma (int) : 計算MA的時間週期
        """
        self.n_ma = n_ma
        self.display_name = f"MA_{self.n_ma}"
        self.info = IndicatorInfo(
            name="MA", 
            display_name=[self.display_name],
            params={"period" : self.n_ma}
        )
        
    def apply(self, df : pd.DataFrame) -> pd.DataFrame:
        df_ana = df.copy()
        
        df_ana[self.display_name] = df_ana.close.rolling(window=self.n_ma, min_periods=self.n_ma).mean()

        return df_ana
    
    def get_info(self) -> IndicatorInfo:
        return self.info
    
    def describe(self)-> str:
        info = self.get_info()
        
        param_descriptions = []
        param_str = ", ".join(f"{k}: {v}" for k, v in info.params.items())
        param_descriptions.append(param_str)
        
        # 使用更美观的多行格式
        description = f"""📊 指標說明: 簡單移動平均線 (Simple Moving Average)

        參數配置:
        {chr(10).join('  • ' + desc for desc in param_descriptions)}

        特點:
        • 追蹤價格趨勢
        • 平滑短期波動
        • 提供技術分析支持
        • 所有歷史數據權重相等（與EMA不同）
        
        與EMA的差異:
        • MA：簡單移動平均，所有數據點權重相同
        • EMA：指數移動平均，近期數據權重較高
        """
        return description


class BIAS(Indicator):
    def __init__(self, n_ema :int = 20):
        """
        Args:
            n_ema (int) : 計算移動均線與收盤價的差值 並計算百分比
        """
        self.n_ema = n_ema
        self.display_name = f"BIAS_{self.n_ema}"
        self.ema_indicator = EMA(self.n_ema)
    
        self.info = IndicatorInfo(
                name="BIAS", 
                display_name=[self.display_name],
                params={
                    "period" : self.n_ema
                }
        )
    
    def apply(self, df : pd.DataFrame) -> pd.DataFrame:
        df_ana = df.copy()

        if self.ema_indicator.display_name not in df_ana.columns:
            df_ana = self.ema_indicator.apply(df_ana)

        df_ana[self.display_name] = (df_ana.close - df_ana[self.ema_indicator.display_name]) / df_ana[self.ema_indicator.display_name] * 100

        return df_ana
    
    def get_info(self):
        return self.info

    
    def describe(self)-> str:
        info = self.get_info()
        
        param_descriptions = []
        param_str = ", ".join(f"{k}: {v}" for k, v in info.params.items())
        param_descriptions.append(param_str)
        
        return f"""
        指標說明:
        收盤價與移動均線的差值與移動均線的比值
        
        參數配置:
        {chr(10).join('  • ' + desc for desc in param_descriptions)}
        """


class Engulfing(Indicator):
    def __init__(self, factor: float = 1.1):
        """
        吞沒形態（Engulfing Pattern）指標
        
        Args:
            factor (float): 吞沒倍數，當前K線實體必須大於前一根的此倍數。默認為 1.1
        """
        self.factor = factor
        self.display_name = "ENGULFING"
        self.info = IndicatorInfo(
            name="Engulfing",
            display_name=[self.display_name],
            params={
                "factor": float(self.factor)
            }
        )
    
    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        計算吞沒形態指標
        
        吞沒形態判斷條件：
        1. 當前K線方向與前一根相反（陽線/陰線相反）
        2. 當前K線實體大於前一根的指定倍數（默認1.1倍）
        
        這是一個反轉信號：
        - 看漲吞沒（Bullish Engulfing）：前一根為陰線，當前為陽線，且當前實體大於前一根
        - 看跌吞沒（Bearish Engulfing）：前一根為陽線，當前為陰線，且當前實體大於前一根
        
        Returns:
            pd.DataFrame: 包含 ENGULFING 列的 DataFrame
        """
        df_ana = df.copy()
        
        # 計算當前K線的方向和實體大小
        price_diff = df_ana.close - df_ana.open
        body_size = price_diff.abs()
        direction = pd.Series([1 if x >= 0 else -1 for x in price_diff], index=df_ana.index)
        
        # 計算前一根K線的方向和實體大小
        direction_prev = direction.shift(1)
        body_size_prev = body_size.shift(1)
        
        # 判斷是否為吞沒形態
        # 1. 方向相反（且前一根不為空）
        direction_opposite = (direction != direction_prev) & direction_prev.notna()
        # 2. 當前實體大於前一根的指定倍數（且前一根不為空）
        body_larger = (body_size > (body_size_prev * self.factor)) & body_size_prev.notna()
        
        # 同時滿足兩個條件才為吞沒形態
        df_ana[self.display_name] = direction_opposite & body_larger
        
        # 處理 NaN 值（第一行沒有前一根K線）
        df_ana[self.display_name] = df_ana[self.display_name].fillna(False)
        
        return df_ana
    
    def get_info(self) -> IndicatorInfo:
        return self.info
    
    def describe(self) -> str:
        info = self.get_info()
        
        param_descriptions = []
        param_str = ", ".join(f"{k}: {v}" for k, v in info.params.items())
        param_descriptions.append(param_str)
        
        return f"""
        指標說明:
            吞沒形態（Engulfing Pattern）是一種K線反轉形態，表示趨勢可能發生反轉。
            
            判斷條件：
            1. 當前K線方向與前一根相反（陽線/陰線相反）
            2. 當前K線實體大於前一根的指定倍數（默認 {self.factor} 倍）
            
            形態類型：
            • 看漲吞沒（Bullish Engulfing）：
              - 前一根為陰線（下跌），當前為陽線（上漲）
              - 當前陽線完全吞沒前一根陰線
              - 通常出現在下跌趨勢底部，預示可能反轉上漲
            
            • 看跌吞沒（Bearish Engulfing）：
              - 前一根為陽線（上漲），當前為陰線（下跌）
              - 當前陰線完全吞沒前一根陽線
              - 通常出現在上漲趨勢頂部，預示可能反轉下跌
            
            使用建議：
            • 吞沒形態是反轉信號，建議結合其他技術指標確認
            • 在趨勢明確的市場中，吞沒形態的可信度更高
            • 實體越大、成交量越大，信號越可靠
        
        參數配置:
        {chr(10).join('  • ' + desc for desc in param_descriptions)}
        """
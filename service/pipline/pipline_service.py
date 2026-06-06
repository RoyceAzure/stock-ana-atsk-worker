from ast import List
from models.pipline_model.data_sink import IDataSink
from typing import Callable, Tuple, Optional, TypeVar, Generic
import pandas as pd
from models.pipline_model.data_set import IDataSet


T = TypeVar("T", pd.DataFrame)

class PipelineStage(Generic[T]):
    def __init__(self, process_func: Callable[[T], T], name: str = None):
        self.process_func = self._wrap_process_func(process_func)
        self.name = name or process_func.__name__

    def _wrap_process_func(self, func: Callable[[T], T]) -> Callable[[T], Tuple[Optional[T], Optional[str]]]:
        def wrapped(df: T) -> Tuple[Optional[T], Optional[str]]:
            try:
                return func(df), None
            except Exception as e:
                return None, str(e)
        return wrapped

    def process(self, df: T) -> Tuple[Optional[T], Optional[str]]:
        return self.process_func(df)
    
    def __str__(self):
        return f"PipelineStage({self.name})"

class Pipline(Generic[T]):
    def __init__(self):
        self.stages: List[PipelineStage] = []
        self.data_set : IDataSet = None
        self.data_sink: IDataSink = None
            
    def set_data_set(self, data_set : IDataSet):
        self.data_set = data_set
        return self
    
    def set_data_sink(self, data_sink : IDataSink):
        self.data_sink = data_sink
        return self
    
    def add_stage(self, stage : PipelineStage):
        self.stages.append(stage)
        return self
        
    def run(self) -> Tuple[Optional[T], Optional[str]]:
        if self.data_set is None:
            return None, "Data set is not set"
        
        if self.data_set is None:
            return None, "Data sink is not set"
        
        print(f"pipline load data")
        df, err = self.data_set.load_data()
        if df is None:
            return None, f"資料筆數不足，無法執行任務"
        
        for stage in self.stages:
            print(f"pipline process stage: {stage.name}")
            df, err = stage.process(df)
            if err is not None:
                return None, f"{stage} stage failed: {err}"
            
        if self.data_sink:
            print(f"pipline save data")
            err = self.data_sink.save_data(df)
            
        if err is not None:
            return df, err

        return df, None
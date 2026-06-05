from pydantic import BaseModel, Field

class SimilarTaskSource(BaseModel):
    # Field(...) 代表必填
    # pattern 確保字串符合 YYYY-MM-DD 格式
    code: str = Field(..., min_length=1)
    start_time: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_time: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    # 固定只能輸入 'd1'
    candle: str = Field(..., pattern="^d1$")
    
class SimilarTaskConfig(BaseModel):
    pca_components: int = Field(default=12, gt=0, description="PCA降維後的目標維度數量")
    
class SimilarTaskParams(BaseModel):
    source_params: SimilarTaskSource
    config: SimilarTaskConfig

class SimilarTaskResult(BaseModel):
    code: str = Field(...)
    end_time: str = Field(...) #rfc3339格式
    similarity: float = Field(...)
    values: list = Field(...)

class SimilarTaskResponse(BaseModel):
    sample_code: str = Field(...)
    candle: str = Field(...) #rfc3339格式
    window_size: int = Field(...)
    sample_values: list = Field(...)
    results: list[SimilarTaskResult] = Field(...)
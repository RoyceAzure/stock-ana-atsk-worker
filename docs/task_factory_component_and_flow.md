# Task Factory 元件圖與流程圖

此文件描述 `service/task/task_factory.py` 的核心元件關係與建立 `TaskCoordinator` 的流程。

## 元件圖（Component Diagram）

```mermaid
graph TD
    TE[TaskEvent event_name] --> TCF[TaskCoordinatorFactory]
    TH[TaskEventHelper] --> TCF
    TR[TaskHandlerRegistry] --> TCF
    TCF --> TC[TaskCoordinator]
    TCF --> TR
    TR --> TF[TaskHandlerFactory]
    TR --> PH[PreProcessPandasTaskProcessor]
    PG[PostgreSQL Connection] --> PH
    DK[DuckDB Connection] --> PH
    BM[BlobParquetMerger] --> PH
    PH --> HD[TaskHandler]
    HD --> TC
```

## 流程圖（Flow Diagram）

```mermaid
graph TD
    S1[Start create_coordinator_for_task] --> S2{Registry exists}
    S2 -->|No| S3[Build default registry]
    S3 --> S4[Register EventName PREPROCESS]
    S4 --> S5[Create TaskCoordinatorFactory]
    S2 -->|Yes| S5
    S5 --> S6[Read task_event event_name]
    S6 --> S7[Registry create handler]
    S7 --> S8[Create TaskCoordinator with helper and handler]
    S8 --> S9[Return coordinator]
```

## 備註

- `TaskHandlerRegistry` 以 `event_name` 作為 key，不使用 `event_stage`。
- 目前預設僅註冊 `EventName.PREPROCESS`。
- 若有新任務（例如 backtesting），可擴充新的 `register(EventName.X, factory)`。

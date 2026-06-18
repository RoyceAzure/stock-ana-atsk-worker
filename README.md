# stock-ana-task-worker

從雲端 queue 接收任務並執行的 worker。設定可寫在 `.env` 或系統環境變數（**環境變數優先於 `.env`**）。

```bash
cp .env.example .env
# 編輯 .env 後啟動
python main.py
# 或
python main.py --mode consumer
```

---

## 命令列參數

| 參數 | 必填 | 預設 | 說明 |
|---|---|:---:|---|
| `--mode` | 否 | `consumer` | 執行模式。目前僅 `consumer` 可用 |

也可用環境變數 `WORKER_MODE`（`--mode` 優先）。

| `--mode` 值 | 說明 |
|---|---|
| `consumer` | 啟動 queue worker（目前支援） |
| `oneshot` / `migrate` / `health` | 尚未實作 |

---

## 環境變數

### 必填（GCP worker）

| 變數 | 說明 |
|---|---|
| `GCP_PROJECT_ID` | GCP 專案 ID |
| `GCP_SUBSCRIPTION_ID` | Pub/Sub 訂閱名稱（此 Pod 監聽的 queue） |
| `OBJECT_STORAGE_BUCKET_BASE_PATH` | GCS 寫入路徑，格式 `bucket名稱/前綴` |
| `GCS_HMAC_ACCESS_KEY` | GCS HMAC 金鑰（DuckDB 讀寫 GCS 必填） |
| `GCS_HMAC_SECRET_KEY` | GCS HMAC 密鑰 |

### 建議設定

| 變數 | 預設 | 說明 |
|---|---|---|
| `CLOUD_PROVIDER` | `gcp` | 雲端廠商（目前僅支援 `gcp`） |
| `WORKER_TASK_TYPES` | `preprocessing` | 此 Pod 處理的任務類型，逗號分隔。合法值：`preprocessing`、`backtesting`、`full_backtest`、`buy_sell_mark`、`similarity` |
| `STORAGE_BACKEND` | `gcs` | 物件儲存後端；`CLOUD_PROVIDER=gcp` 時須為 `gcs` |
| `PG_HOST` | `localhost` | PostgreSQL 主機 |
| `PG_DATABASE` | `sexy_stock` | 資料庫名稱 |
| `PG_USER` | `postgres` | 資料庫使用者 |
| `PG_PASSWORD` | `password` | 資料庫密碼 |
| `PG_PORT` | `5432` | 資料庫埠 |

### 選填（調校用）

| 變數 | 預設 | 說明 |
|---|---|---|
| `WORKER_MODE` | `consumer` | 等同 `--mode`，CLI 未指定時使用 |
| `DUCKDB_POOL_SIZE` | `10` | DuckDB 連線池大小 |
| `PG_POOL_MIN_CONN` | `1` | PostgreSQL 連線池最小連線數 |
| `PG_POOL_MAX_CONN` | `10` | PostgreSQL 連線池最大連線數 |
| `PUBSUB_BATCH_SIZE` | `10` | 單次從 Pub/Sub 拉取的訊息數 |
| `PUBSUB_VISIBILITY_TIMEOUT` | `30` | 訊息 ack 期限（秒），逾時會重派 |
| `PUBSUB_PULL_TIMEOUT` | `5.0` | 無訊息時 pull 等待時間（秒） |
| `SHUTDOWN_DRAIN_TIMEOUT` | `30.0` | 關閉時等待進行中任務完成的秒數 |
| `GCS_USE_ADC` | `false` | `true` 時 fsspec/gcsfs 使用 GCP 預設憑證（DuckDB 仍須 HMAC） |

---

## 快速範例（`.env`）

```env
WORKER_MODE=consumer
CLOUD_PROVIDER=gcp
WORKER_TASK_TYPES=preprocessing

GCP_PROJECT_ID=my-project
GCP_SUBSCRIPTION_ID=preprocess-sub

STORAGE_BACKEND=gcs
OBJECT_STORAGE_BUCKET_BASE_PATH=my-bucket/data
GCS_HMAC_ACCESS_KEY=your-access-key
GCS_HMAC_SECRET_KEY=your-secret-key

PG_HOST=localhost
PG_DATABASE=sexy_stock
PG_USER=postgres
PG_PASSWORD=your-password
PG_PORT=5432
```

---

## 延伸說明

組裝與變數對應細節見 [docs/worker_config_assembly.md](docs/worker_config_assembly.md)。

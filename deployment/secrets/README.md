# 本機部署用 GCP 憑證（勿提交）

此目錄存放 **僅供本機開發與 kind** 使用的 Service Account JSON，已加入 `.gitignore`。

## 檔案放置

將從 GCP Console 下載的 SA 金鑰放到：

```
deployment/secrets/gcp-sa.json
```

（檔名可自訂，但建議固定為 `gcp-sa.json`，避免把專案 ID 寫進路徑。）

## `.env` 設定

```env
GCP_AUTH_MODE=service_account_json
GCP_SA_KEY_FILE=deployment/secrets/gcp-sa.json
```

本機直接 `python main.py` 時，請在專案根目錄執行（路徑為相對於 cwd）。

## kind / K8s Secret

Pod 內掛載路徑建議為 `/var/secrets/google/key.json`：

```bash
kubectl create secret generic gcp-sa-key \
  --from-file=key.json=deployment/secrets/gcp-sa.json \
  -n <K8S_NAMESPACE> \
  --dry-run=client -o yaml | kubectl apply -f -
```

Deployment 環境變數：

```env
GCP_AUTH_MODE=service_account_json
GCP_SA_KEY_FILE=/var/secrets/google/key.json
```

## 注意

- **GKE 正式環境**請用 Workload Identity，不要將此 JSON 掛進 cluster。
- 若金鑰曾意外 commit，請在 GCP 旋轉金鑰並撤銷舊 key。

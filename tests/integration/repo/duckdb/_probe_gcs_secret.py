import os
import sys

import duckdb
import google.auth
import google.auth.transport.requests

sys.path.insert(0, os.getcwd())

from infra.repo.object_storage import object_uri
from tests.integration.repo.duckdb.conftest import build_gcs_storage_config, gcs_test_bucket

adc = os.path.join(os.environ["APPDATA"], "gcloud", "application_default_credentials.json")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = adc

creds, _ = google.auth.default()
creds.refresh(google.auth.transport.requests.Request())
token = creds.token

cfg = build_gcs_storage_config()
uri = object_uri(cfg, gcs_test_bucket(), "test/duckdb/probe-bearer.parquet")

con = duckdb.connect(":memory:")
con.execute("INSTALL httpfs; LOAD httpfs;")
con.execute(f"CREATE OR REPLACE SECRET s (TYPE GCS, bearer_token '{token}')")
con.execute(f"COPY (SELECT 1 AS id, '2330' AS code) TO '{uri}' (FORMAT PARQUET, CODEC 'SNAPPY')")
rows = con.execute(f"SELECT * FROM read_parquet('{uri}') ORDER BY id").fetchall()
print("SUCCESS", rows)

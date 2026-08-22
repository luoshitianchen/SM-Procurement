# SM Procurement

采购管理：申请、供应商、询价、订单、验收和付款。

```powershell
git clone https://github.com/luoshitianchen/SM-Procurement.git
cd SM-Procurement
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8530
```

接口：`/health`、`/readyz`、`/api/overview`、`/api/items`、`/api/ops/metrics`、`/api/crypto/status`。

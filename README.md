# 🔍 EVM Wallet Tracker — GitHub Actions

Track ví EVM 24/7 miễn phí, không cần server. Danh sách ví ẩn hoàn toàn trong GitHub Secrets.

---

## 📁 Cấu trúc

```
wallet-tracker/
├── tracker.py                     # script chính
├── chains.json                    # chain tuỳ chỉnh (tuỳ chọn)
├── seen_txs.json                  # state tự động (không cần đụng)
└── .github/workflows/tracker.yml  # chạy mỗi 5 phút
```

> Không có `wallets.json` — danh sách ví lưu trong GitHub Secrets, không ai thấy được.

---

## 🚀 Setup từng bước

### Bước 1 — Tạo repo GitHub (Public)

1. Vào [github.com/new](https://github.com/new)
2. Đặt tên repo, ví dụ: `wallet-tracker`
3. Chọn **Public** (để dùng Actions miễn phí không giới hạn)
4. Nhấn **Create repository**

---

### Bước 2 — Push code lên

```bash
cd wallet-tracker-gh
git init
git add .
git commit -m "init"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/wallet-tracker.git
git push -u origin main
```

---

### Bước 3 — Tạo Telegram Bot

1. Mở Telegram → tìm **@BotFather** → `/newbot`
2. Lấy **Bot Token** (dạng `123456:AAFxxx...`)
3. Lấy **Chat ID**: forward tin nhắn tới **@userinfobot**

---

### Bước 4 — Thêm Secrets vào GitHub

Vào repo → **Settings → Secrets and variables → Actions → New repository secret**

#### Bắt buộc

| Secret | Giá trị |
|--------|---------|
| `TELEGRAM_TOKEN` | Bot token từ BotFather |
| `TELEGRAM_CHAT_ID` | Chat ID của bạn |
| `WALLETS_JSON` | Danh sách ví (xem format bên dưới) |

#### Tuỳ chọn (khuyến nghị để tránh rate limit)

| Secret | Lấy ở đâu |
|--------|-----------|
| `ETHERSCAN_API_KEY` | etherscan.io/apis |
| `BSCSCAN_API_KEY` | bscscan.com/apis |
| `POLYGONSCAN_API_KEY` | polygonscan.com/apis |
| `ARBISCAN_API_KEY` | arbiscan.io/apis |
| `BASESCAN_API_KEY` | basescan.org/apis |

---

### Format WALLETS_JSON

Copy đoạn JSON này, sửa địa chỉ/label/chain rồi paste vào secret `WALLETS_JSON`:

```json
[{"address":"0xADDRESS_1","label":"Ví chính","chains":["eth","bsc"],"active":true},{"address":"0xADDRESS_2","label":"Ví trading","chains":["arbitrum","base"],"active":true}]
```

> Phải là **1 dòng duy nhất**. Dùng [jsonformatter.org/json-minify](https://jsonformatter.org/json-minify) để minify nếu cần.

**Chains hỗ trợ sẵn:** `eth` `bsc` `polygon` `arbitrum` `optimism` `base` `avalanche`

---

### Bước 5 — Bật Actions và chạy thử

Vào repo → tab **Actions** → nhấn **Enable Actions**

Chạy thử thủ công: **Actions → EVM Wallet Tracker → Run workflow**

---

## ✏️ Thêm/sửa ví

Vào **Settings → Secrets → WALLETS_JSON** → sửa JSON → Save.
Lần chạy tiếp theo (~5 phút) tự áp dụng.

---

## 🧪 Chạy local để test

```bash
pip install httpx

# Tạo wallets.json tạm (script tự fallback sang file này khi không có WALLETS_JSON env)
echo '[{"address":"0xYOUR_ADDRESS","label":"Test","chains":["eth"],"active":true}]' > wallets.json

export TELEGRAM_TOKEN="your_token"
export TELEGRAM_CHAT_ID="your_chat_id"

python tracker.py
```

---

## ⚠️ Lưu ý

- Lần **đầu tiên** chạy không gửi notify (chỉ lưu state để tránh spam)
- `seen_txs.json` auto-commit sau mỗi lần chạy (chỉ chứa tx hash, không nhạy cảm)
- GitHub cron có thể delay thêm vài phút vào giờ cao điểm

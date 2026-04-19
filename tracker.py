#!/usr/bin/env python3
"""
EVM Wallet Tracker — GitHub Actions version
Chạy 1 lần, kiểm tra tx mới, gửi Telegram, lưu state, thoát.

Danh sách ví đọc từ WALLETS_JSON (GitHub Secret) hoặc wallets.json (local test).
"""

import json
import os
import httpx
import asyncio
from datetime import datetime

# ─── CONFIG từ GitHub Secrets ───────────────────────────────────────
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

CHAIN_API_KEYS = {
    "eth":       os.environ.get("ETHERSCAN_API_KEY", ""),
    "bsc":       os.environ.get("BSCSCAN_API_KEY", ""),
    "polygon":   os.environ.get("POLYGONSCAN_API_KEY", ""),
    "arbitrum":  os.environ.get("ARBISCAN_API_KEY", ""),
    "optimism":  os.environ.get("OPTIMISM_API_KEY", ""),
    "base":      os.environ.get("BASESCAN_API_KEY", ""),
    "avalanche": os.environ.get("SNOWTRACE_API_KEY", ""),
}

# ─── FILES ──────────────────────────────────────────────────────────
SEEN_TX_FILE = "seen_txs.json"
CHAINS_FILE  = "chains.json"

# ─── CHAINS mặc định ────────────────────────────────────────────────
DEFAULT_CHAINS = {
    "eth": {
        "name": "Ethereum", "symbol": "ETH", "icon": "⟠",
        "api": "https://api.etherscan.io/api",
        "explorer": "https://etherscan.io",
    },
    "bsc": {
        "name": "BNB Chain", "symbol": "BNB", "icon": "🔶",
        "api": "https://api.bscscan.com/api",
        "explorer": "https://bscscan.com",
    },
    "polygon": {
        "name": "Polygon", "symbol": "POL", "icon": "🟣",
        "api": "https://api.polygonscan.com/api",
        "explorer": "https://polygonscan.com",
    },
    "arbitrum": {
        "name": "Arbitrum", "symbol": "ETH", "icon": "🔵",
        "api": "https://api.arbiscan.io/api",
        "explorer": "https://arbiscan.io",
    },
    "optimism": {
        "name": "Optimism", "symbol": "ETH", "icon": "🔴",
        "api": "https://api-optimistic.etherscan.io/api",
        "explorer": "https://optimistic.etherscan.io",
    },
    "base": {
        "name": "Base", "symbol": "ETH", "icon": "🔷",
        "api": "https://api.basescan.org/api",
        "explorer": "https://basescan.org",
    },
    "avalanche": {
        "name": "Avalanche", "symbol": "AVAX", "icon": "🔺",
        "api": "https://api.snowtrace.io/api",
        "explorer": "https://snowtrace.io",
    },
}

# ─── HELPERS ────────────────────────────────────────────────────────
def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def format_value(wei: str, decimals=18, symbol="ETH") -> str:
    try:
        val = int(wei) / (10 ** decimals)
        if val == 0:
            return f"0 {symbol}"
        return f"{val:.4f} {symbol}" if val >= 0.0001 else f"<0.0001 {symbol}"
    except:
        return f"? {symbol}"

def build_message(tx: dict, wallet: dict, chain: dict, direction: str) -> str:
    icon  = "📥" if direction == "IN" else "📤"
    label = wallet.get("label") or wallet["address"][:8] + "..."
    value = format_value(tx.get("value", "0"), symbol=chain["symbol"])

    from_addr = tx.get("from", "")
    to_addr   = tx.get("to", "")
    from_s = from_addr[:8] + "…" + from_addr[-4:]
    to_s   = to_addr[:8]   + "…" + to_addr[-4:]

    ts = int(tx.get("timeStamp", 0))
    time_str = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M UTC") if ts else "?"

    tx_hash = tx.get("hash", "")
    tx_link = f"{chain['explorer']}/tx/{tx_hash}"

    return (
        f"{icon} <b>{direction}</b>  {chain['icon']} {chain['name']}\n"
        f"👛 <b>{label}</b>\n"
        f"💰 {value}\n"
        f"📤 From: <code>{from_s}</code>\n"
        f"📥 To:   <code>{to_s}</code>\n"
        f"⏰ {time_str}\n"
        f"🔗 <a href='{tx_link}'>{tx_hash[:10]}…{tx_hash[-6:]}</a>"
    )

def load_wallets() -> list:
    """
    Ưu tiên đọc từ WALLETS_JSON env (GitHub Secret).
    Fallback sang wallets.json khi chạy local.
    """
    wallets_raw = os.environ.get("WALLETS_JSON", "").strip()
    if wallets_raw:
        try:
            wallets = json.loads(wallets_raw)
            print(f"✅ Đọc {len(wallets)} ví từ WALLETS_JSON secret")
            return wallets
        except Exception as e:
            print(f"❌ Lỗi parse WALLETS_JSON: {e}")
            return []

    # Fallback local
    wallets = load_json("wallets.json", [])
    if wallets:
        print(f"ℹ️  Đọc {len(wallets)} ví từ wallets.json (local mode)")
    return wallets

# ─── ASYNC CORE ──────────────────────────────────────────────────────
async def fetch_txs(address: str, chain_id: str, chain: dict, client: httpx.AsyncClient):
    params = {
        "module": "account", "action": "txlist",
        "address": address,
        "page": 1, "offset": 20, "sort": "desc",
    }
    api_key = CHAIN_API_KEYS.get(chain_id, "")
    if api_key:
        params["apikey"] = api_key
    try:
        r = await client.get(chain["api"], params=params, timeout=15)
        data = r.json()
        if data.get("status") == "1":
            return data.get("result", [])
    except Exception as e:
        print(f"  ⚠️  Fetch failed {address[:8]}… on {chain_id}: {e}")
    return []

async def send_telegram(msg: str, client: httpx.AsyncClient):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("  ⚠️  Telegram chưa cấu hình")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = await client.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }, timeout=10)
        if r.status_code != 200:
            print(f"  ❌ Telegram error: {r.text}")
    except Exception as e:
        print(f"  ❌ Telegram failed: {e}")

async def run():
    wallets = load_wallets()
    if not wallets:
        print("⚠️  Không có ví nào. Set WALLETS_JSON secret hoặc tạo wallets.json")
        return

    seen_txs = load_json(SEEN_TX_FILE, {})
    chains   = {**DEFAULT_CHAINS, **load_json(CHAINS_FILE, {})}

    print(f"🔍 Tracking {len(wallets)} ví...\n")
    total_new = 0

    async with httpx.AsyncClient() as client:
        for wallet in wallets:
            if not wallet.get("active", True):
                continue

            address      = wallet["address"].lower()
            label        = wallet.get("label") or address[:8] + "..."
            watch_chains = wallet.get("chains", ["eth"])

            for chain_id in watch_chains:
                chain = chains.get(chain_id)
                if not chain:
                    print(f"  ⚠️  Chain '{chain_id}' không tìm thấy, bỏ qua")
                    continue

                key          = f"{address}:{chain_id}"
                seen         = set(seen_txs.get(key, []))
                is_first_run = key not in seen_txs

                txs     = await fetch_txs(address, chain_id, chain, client)
                new_txs = [tx for tx in txs if tx.get("hash") and tx["hash"] not in seen]

                if new_txs:
                    print(f"  ✅ {label} [{chain_id}]: {len(new_txs)} tx mới")
                    total_new += len(new_txs)

                    if not is_first_run:
                        for tx in reversed(new_txs):
                            direction = "OUT" if tx.get("from", "").lower() == address else "IN"
                            msg = build_message(tx, wallet, chain, direction)
                            await send_telegram(msg, client)
                            await asyncio.sleep(0.3)
                    else:
                        print(f"     (lần đầu chạy — lưu state, chưa gửi notify)")

                    for tx in new_txs:
                        seen.add(tx["hash"])
                else:
                    print(f"  — {label} [{chain_id}]: không có tx mới")

                seen_txs[key] = list(seen)[-500:]
                await asyncio.sleep(0.2)

    save_json(SEEN_TX_FILE, seen_txs)
    print(f"\n✅ Xong. Tổng tx mới: {total_new}")

if __name__ == "__main__":
    asyncio.run(run())

import time
import psycopg2
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')

OHIO_URL = "postgresql://neondb_owner:npg_62aSwNvWgUBT@ep-holy-lake-ayhswebt.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require"
SINGAPORE_URL = "postgresql://neondb_owner:npg_WBjT5wU1lrzy@ep-restless-haze-azsi5s6f-pooler.c-3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

def test_database_speed(name, url):
    print(f"\n" + "-" * 50)
    print(f"🚀 Testing {name}...")
    print("-" * 50)
    
    # 1. Connection Latency
    t0 = time.perf_counter()
    try:
        conn = psycopg2.connect(url)
        conn_time = (time.perf_counter() - t0) * 1000
        cur = conn.cursor()
        print(f"  ⚡ Connection Handshake: {conn_time:.1f} ms")
    except Exception as e:
        print(f"  ❌ Connection Failed: {e}")
        return None

    # 2. Simple Ping (SELECT 1)
    ping_times = []
    for _ in range(5):
        t0 = time.perf_counter()
        cur.execute("SELECT 1")
        cur.fetchone()
        ping_times.append((time.perf_counter() - t0) * 1000)
    avg_ping = sum(ping_times) / len(ping_times)
    print(f"  ⚡ Round-Trip Network Ping (Avg of 5): {avg_ping:.1f} ms")

    # 3. Complex Balance Calculation (Real App Query)
    t0 = time.perf_counter()
    cur.execute("""
        SELECT account_code, COALESCE(SUM(debit), 0) - COALESCE(SUM(credit), 0)
        FROM jv_entries
        WHERE account_code IN ('AST-101', 'AST-102', 'AST-103')
        GROUP BY account_code
    """)
    cur.fetchall()
    bal_time = (time.perf_counter() - t0) * 1000
    print(f"  ⚡ General Ledger Balance Calculation: {bal_time:.1f} ms")

    # 4. Fetch 50 Cash Book Rows (Tab Render Query)
    t0 = time.perf_counter()
    cur.execute("SELECT id, date, voucher_no, particulars, debit_amount, credit_amount, balance FROM cash_book ORDER BY id DESC LIMIT 50")
    cur.fetchall()
    fetch_time = (time.perf_counter() - t0) * 1000
    print(f"  ⚡ Fetching 50 Cash Book Rows: {fetch_time:.1f} ms")

    cur.close()
    conn.close()
    
    return {
        "conn": conn_time,
        "ping": avg_ping,
        "balance": bal_time,
        "fetch": fetch_time
    }

def main():
    print("=" * 60)
    print("📊 REAL-TIME DATABASE SPEED BENCHMARK (OHIO vs SINGAPORE)")
    print("=" * 60)
    
    ohio_res = test_database_speed("OHIO (USA)", OHIO_URL)
    sgp_res = test_database_speed("SINGAPORE (ASIA)", SINGAPORE_URL)
    
    if ohio_res and sgp_res:
        print("\n" + "=" * 60)
        print("🏆 FINAL PERFORMANCE COMPARISON:")
        print("=" * 60)
        print(f"{'Operation':<35} | {'Ohio (US)':<12} | {'Singapore':<12} | {'Speedup':<10}")
        print("-" * 75)
        
        ops = [
            ("Connection Handshake", "conn"),
            ("Network Round-Trip Ping", "ping"),
            ("Ledger Balance Calculation", "balance"),
            ("Fetching 50 Cash Book Rows", "fetch"),
        ]
        
        for label, key in ops:
            o_val = ohio_res[key]
            s_val = sgp_res[key]
            speedup = o_val / s_val if s_val > 0 else 1.0
            print(f"{label:<35} | {o_val:>8.1f} ms | {s_val:>8.1f} ms | {speedup:>7.1f}x Faster")
        print("=" * 75)

if __name__ == "__main__":
    main()

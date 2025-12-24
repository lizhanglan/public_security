import os
import sys
from pathlib import Path
import argparse
import json
import psycopg2

def _try_import_db_config():
    candidates = [
        Path(__file__).resolve().parents[1] / "backend" / "app" / "迁移",
        Path(os.getcwd()) / "backend" / "app" / "迁移",
    ]
    for p in candidates:
        if (p / "db_config.py").exists():
            if str(p) not in sys.path:
                sys.path.insert(0, str(p))
            try:
                from db_config import db_config
                return db_config
            except Exception:
                continue
    return None

def _connect():
    db_cfg = _try_import_db_config()
    if not db_cfg:
        raise RuntimeError("无法导入 db_config.py")
    return psycopg2.connect(**db_cfg.opengauss_config)

def _fetch_activity(cur):
    cur.execute("""
        SELECT
          pid,
          usename,
          datname,
          application_name,
          client_addr,
          state,
          wait_event_type,
          wait_event,
          query_start,
          now() - query_start AS duration,
          query
        FROM pg_stat_activity
        ORDER BY query_start NULLS LAST
    """)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]

def _fetch_blocking(cur):
    cur.execute("""
        SELECT
          bl.pid               AS blocked_pid,
          a.usename            AS blocked_user,
          bl.locktype,
          bl.mode              AS blocked_mode,
          kl.pid               AS blocking_pid,
          ka.usename           AS blocking_user,
          kl.mode              AS blocking_mode,
          a.query              AS blocked_query,
          ka.query             AS blocking_query,
          now() - a.query_start AS blocked_duration
        FROM pg_locks bl
        JOIN pg_stat_activity a ON bl.pid = a.pid
        JOIN pg_locks kl ON bl.locktype = kl.locktype
                          AND bl.database IS NOT DISTINCT FROM kl.database
                          AND bl.relation IS NOT DISTINCT FROM kl.relation
                          AND bl.transactionid IS NOT DISTINCT FROM kl.transactionid
                          AND bl.classid IS NOT DISTINCT FROM kl.classid
                          AND bl.objid IS NOT DISTINCT FROM kl.objid
                          AND bl.pid <> kl.pid
        JOIN pg_stat_activity ka ON kl.pid = ka.pid
        WHERE NOT bl.granted
    """)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-duration-ms", type=int, default=1000)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        conn = _connect()
        cur = conn.cursor()
        activity = _fetch_activity(cur)
        blocking = _fetch_blocking(cur)
        long_running = []
        for row in activity:
            d = row.get("duration")
            if d is not None:
                ms = int(d.total_seconds() * 1000)
                if ms >= args.min_duration_ms:
                    row["_duration_ms"] = ms
                    long_running.append(row)
        if args.json:
            print(json.dumps({
                "long_running": long_running,
                "blocking": blocking
            }, ensure_ascii=False, default=str, indent=2))
        else:
            print(f"长时间运行语句阈值: {args.min_duration_ms} ms")
            print(f"长时间运行语句数量: {len(long_running)}")
            for i, r in enumerate(long_running[:20], 1):
                print(f"{i}. pid={r['pid']} user={r['usename']} db={r['datname']} ms={r['_duration_ms']}")
                print(f"   {r['query']}")
            print(f"\n阻塞链路数量: {len(blocking)}")
            for i, b in enumerate(blocking[:20], 1):
                dur = b.get("blocked_duration")
                ms = int(dur.total_seconds() * 1000) if dur else 0
                print(f"{i}. blocked_pid={b['blocked_pid']} blocking_pid={b['blocking_pid']} ms={ms} lock={b['locktype']} mode={b['blocked_mode']}->{b['blocking_mode']}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"执行失败: {e}")

if __name__ == "__main__":
    main()


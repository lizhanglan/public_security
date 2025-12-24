import os
import sys
from pathlib import Path
import psycopg2
import json

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

def _fetch_bgwriter(cur):
    cur.execute("""
        SELECT
          checkpoints_timed,
          checkpoints_req,
          buffers_checkpoint,
          buffers_clean,
          maxwritten_clean,
          checkpoint_write_time,
          checkpoint_sync_time
        FROM pg_stat_bgwriter
    """)
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, cur.fetchone()))

def _advise(stats):
    adv = []
    timed = stats.get("checkpoints_timed", 0)
    req = stats.get("checkpoints_req", 0)
    write_ms = stats.get("checkpoint_write_time", 0)
    sync_ms = stats.get("checkpoint_sync_time", 0)
    if req > timed:
        adv.append("检查点多为请求触发，评估增大 max_wal_size 或 checkpoint_timeout")
    if write_ms + sync_ms > 30000:
        adv.append("检查点写入/同步耗时较高，评估磁盘带宽与参数配置")
    if stats.get("buffers_clean", 0) < stats.get("buffers_checkpoint", 0) / 2:
        adv.append("后台清理较少，相对检查点写入偏多，评估 shared_buffers 与写入模式")
    if not adv:
        adv.append("检查点与 WAL 状态正常")
    return adv

def main():
    try:
        conn = _connect()
        cur = conn.cursor()
        stats = _fetch_bgwriter(cur)
        adv = _advise(stats)
        print(json.dumps({"stats": stats, "advice": adv}, ensure_ascii=False, indent=2))
        cur.close()
        conn.close()
    except Exception as e:
        print(f"执行失败: {e}")

if __name__ == "__main__":
    main()


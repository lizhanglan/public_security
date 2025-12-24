import os
import sys
from pathlib import Path
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

def _fmt_value(v):
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    sl = s.lower()
    if sl in ("on", "off"):
        return sl
    return "'" + s.replace("'", "''") + "'"

def _apply_settings(cur, settings):
    for k, v in settings.items():
        q = f"ALTER SYSTEM SET {k} TO {_fmt_value(v)}"
        cur.execute(q)

def main():
    print("openGauss 日志配置基线应用")
    db_cfg = _try_import_db_config()
    if not db_cfg:
        print("无法导入 db_config.py，请在项目根目录运行或设置环境变量")
        return
    cfg = db_cfg.opengauss_config
    try:
        conn = psycopg2.connect(**cfg)
        conn.autocommit = True
        cur = conn.cursor()
        settings = {
            "logging_collector": "on",
            "log_destination": "csvlog",
            "log_line_prefix": "%m [%p] user=%u,db=%d,app=%a,client=%h ",
            "log_min_duration_statement": 1000,
            "log_statement": "ddl",
            "log_rotation_age": "1d",
            "log_rotation_size": "1GB",
            "track_io_timing": "on",
        }
        _apply_settings(cur, settings)
        cur.execute("SELECT pg_reload_conf()")
        print("已应用并重载配置")
    except Exception as e:
        print(f"执行失败: {e}")
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()


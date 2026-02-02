import aiomysql
import time
from app.core.utils import retry_async

# --- 资源管理 ---
class DBPoolManager:
    """管理多个数据库实例的连接池"""
    _pools = {}

    @classmethod
    async def get_pool(cls, conf):
        # 以 IP:PORT 为键复用连接池
        key = f"{conf['ip']}:{conf['port']}"
        if key not in cls._pools:
            cls._pools[key] = await aiomysql.create_pool(
                host=conf["ip"], 
                port=conf["port"], 
                user=conf["user"], 
                password=conf["password"], 
                cursorclass=aiomysql.DictCursor, 
                connect_timeout=3,
                minsize=1, 
                maxsize=5, # 监控查询并发不高，5个连接足够
                autocommit=True
            )
        return cls._pools[key]

# QPS 计算缓存: { "ip:port": {"ts": timestamp, "count": total_queries} }
_qps_cache = {}

class DBMonitor:
    @staticmethod
    @retry_async()
    async def get_basic_status(conf, role="slave"):
        res = {
            "ip": conf["ip"], "role": role, "connected": False,
            "version": "", "uptime": "", "conn_curr": 0, "conn_max": 0, "qps": 0,
            "io": "No", "sql": "No", "delay": -1, "error": None,
            "file": "", "pos": 0, "gtid": "", "read_pos": 0, "exec_pos": 0
        }
        pool = None
        try:
            pool = await DBPoolManager.get_pool(conf)
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # 1. 基础信息
                    await cur.execute("SELECT VERSION() as v")
                    res["version"] = (await cur.fetchone())['v']
                    
                    await cur.execute("SHOW GLOBAL STATUS LIKE 'Threads_connected'")
                    res["conn_curr"] = int((await cur.fetchone())['Value'])
                    
                    await cur.execute("SHOW VARIABLES LIKE 'max_connections'")
                    res["conn_max"] = int((await cur.fetchone())['Value'])

                    await cur.execute("SHOW GLOBAL STATUS LIKE 'Uptime'")
                    uptime = int((await cur.fetchone())['Value'])
                    res["uptime"] = f"{uptime // 86400}天{(uptime % 86400) // 3600}小时"

                    # 2. QPS 计算 (实时速率)
                    await cur.execute("SHOW GLOBAL STATUS LIKE 'Queries'")
                    current_queries = int((await cur.fetchone())['Value'])
                    current_time = time.time()
                    
                    cache_key = f"{conf['ip']}:{conf['port']}"
                    last_stat = _qps_cache.get(cache_key)
                    
                    if last_stat:
                        delta_t = current_time - last_stat['ts']
                        delta_q = current_queries - last_stat['count']
                        if delta_t > 0:
                            res["qps"] = int(delta_q / delta_t)
                    
                    # 更新缓存
                    _qps_cache[cache_key] = {"ts": current_time, "count": current_queries}

                    res["connected"] = True

                    # 3. 主从状态
                    if role == "master":
                        await cur.execute("SHOW MASTER STATUS")
                        m = await cur.fetchone()
                        if m:
                            res["file"] = m.get("File")
                            res["pos"] = m.get("Position")
                    else:
                        await cur.execute("SHOW SLAVE STATUS")
                        s = await cur.fetchone()
                        if s:
                            res["io"] = s.get("Slave_IO_Running")
                            res["sql"] = s.get("Slave_SQL_Running")
                            res["delay"] = s.get("Seconds_Behind_Master") if s.get("Seconds_Behind_Master") is not None else -1
                            res["error"] = s.get("Last_SQL_Error") or s.get("Last_IO_Error")
                            res["file"] = s.get("Master_Log_File")
                            res["read_pos"] = s.get("Read_Master_Log_Pos")
                            res["exec_pos"] = s.get("Exec_Master_Log_Pos")
                            res["gtid"] = s.get("Retrieved_Gtid_Set") or s.get("Executed_Gtid_Set") or "OFF"
        except Exception as e:
            res["error"] = str(e)
        return res

    @staticmethod
    @retry_async()
    async def get_details(conf):
        details = {
            "innodb": {}, "locks": [], "slow_queries": [], "tables": []
        }
        try:
            pool = await DBPoolManager.get_pool(conf)
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # 1. InnoDB Metrics
                    metrics = {}
                    await cur.execute("SHOW VARIABLES LIKE 'innodb_buffer_pool_size'")
                    row = await cur.fetchone()
                    if row: metrics['buffer_pool_mb'] = round(int(row['Value']) / 1024 / 1024, 2)
                    
                    await cur.execute("SHOW GLOBAL STATUS LIKE 'Innodb_buffer_pool_reads'")
                    reads = int((await cur.fetchone())['Value'])
                    await cur.execute("SHOW GLOBAL STATUS LIKE 'Innodb_buffer_pool_read_requests'")
                    reqs = int((await cur.fetchone())['Value'])
                    metrics['hit_rate'] = f"{(1 - reads/reqs)*100:.2f}%" if reqs > 0 else "100%"
                    details['innodb'] = metrics

                    # 2. Locks
                    await cur.execute("""
                        SELECT id, user, host, db, command, time, state, info 
                        FROM information_schema.processlist 
                        WHERE state LIKE '%lock%' OR (command = 'Sleep' AND time > 300) 
                        LIMIT 5
                    """)
                    details['locks'] = await cur.fetchall()

                    # 3. Slow Queries
                    try:
                        await cur.execute("""
                            SELECT sql_text, timer_wait/1000000000 as time, rows_sent, rows_examined 
                            FROM performance_schema.events_statements_history_long 
                            ORDER BY timer_wait DESC LIMIT 5
                        """)
                        details['slow_queries'] = await cur.fetchall()
                    except:
                        details['slow_queries'] = []

                    # 4. Tables
                    await cur.execute("""
                        SELECT table_schema as db, table_name as tb, 
                        (data_length + index_length)/1024/1024 as size_mb 
                        FROM information_schema.tables 
                        WHERE table_schema NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys') 
                        ORDER BY size_mb DESC LIMIT 5
                    """)
                    details['tables'] = await cur.fetchall()
        except Exception as e:
            details['error'] = str(e)
        return details
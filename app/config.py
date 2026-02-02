import os

class Config:
    # --- 基础配置 ---
    FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    
    # --- 1. 推理集群配置 (SGLang) ---
    # 根据你提供的 Docker 命令整理
    INFERENCE_NODES = [
        # 201 节点 (双卡/双容器)
        {"name": "qwen-201-0123", "ip": "192.168.1.201", "port": 30000},
        {"name": "qwen-201-4567", "ip": "192.168.1.201", "port": 30001},
        # 202 节点 (双卡/双容器)
        {"name": "qwen-202-0123", "ip": "192.168.1.202", "port": 30000},
        {"name": "qwen-202-4567", "ip": "192.168.1.202", "port": 30001},
        # 21 节点 (单容器)
        {"name": "qwen-21-4567",  "ip": "192.168.1.21",  "port": 30001}
    ]

    # --- 2. Zabbix API 配置 ---
    ZABBIX_ENABLED = True
    ZABBIX_API_URL = "http://192.168.1.108/zabbix" 
    ZABBIX_USER = "Admin"
    ZABBIX_PASSWORD = "Xianyu12345@"
    
    # 监控大屏中显示的物理机列表 (需与 Zabbix Hostname/Interface IP 对应)
    MONITOR_IPS = [
        "192.168.1.106", "192.168.1.107", "192.168.1.105", "192.168.1.104", # DB
        "192.168.1.21", "192.168.1.201", "192.168.1.202" # Inference
    ]

    # --- 3. MySQL 监控配置 (业务库) ---
    # IP 来自你上传的 app/config.py
    MASTER = {
        "ip": "192.168.1.106", 
        "port": 3306, 
        "user": "root", 
        "password": os.getenv("DB_ROOT_PASS", "bAm5b&mp") # 默认值防止环境变量未设
    }
    
    SLAVES = [
        {"ip": "192.168.1.107", "port": 3306, "user": "root", "password": os.getenv("DB_ROOT_PASS", "bAm5b&mp"), "server_id": 107},
        {"ip": "192.168.1.105", "port": 3306, "user": "root", "password": os.getenv("DB_ROOT_PASS", "bAm5b&mp"), "server_id": 105},
        {"ip": "192.168.1.104", "port": 3306, "user": "root", "password": os.getenv("DB_ROOT_PASS", "bAm5b&mp"), "server_id": 104}
    ]
    
    # 监控数据存储库 (OpsCenter 自身存储历史数据用)
    # 假设部署在本地或某台机器上，用于存 skipped_repl_errors 表
    MONITOR_DB = {
        "host": "127.0.0.1", 
        "port": 3306,
        "user": "root", 
        "password": "Your_Monitor_DB_Password", 
        "database": "ops_monitor"
    }

    # 其他配置
    CACHE_TTL = 60
    TASK_TIMEOUT = 10
    MAX_CONCURRENT_TASKS = 10
    LOG_PARSE_HOURS = 24
    TIMEZONE = "Asia/Shanghai"

    # 告警阈值
    class ALERTS:
        cpu = 85
        memory = 90
        disk = 90
        swap = 80
        io_util = 90
        conn = 85
        delay = 60
        hit_rate = 95

    # SSH 配置占位
    SSH_CONFIGS = {} 
    @staticmethod
    def get_ssh_config(ip): pass
    @staticmethod
    def all_servers(): return Config.MONITOR_IPS
    @staticmethod
    def get_monitor_db_config(): return Config.MONITOR_DB
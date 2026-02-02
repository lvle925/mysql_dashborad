import asyncio
from datetime import datetime
from app.config import Config
from app.core.zabbix import ZabbixMonitor
from app.core.db import DBMonitor
from app.core.inference import InferenceMonitor

class DataCollector:
    @staticmethod
    async def collect_dashboard_data():
        """自动刷新的轻量数据"""
        tasks = {
            "inf": [InferenceMonitor.check_node(n) for n in Config.INFERENCE_NODES],
            "zabbix": ZabbixMonitor.get_hosts_metrics()
        }
        
        inf_res = await asyncio.gather(*tasks["inf"])
        zabbix_res = await tasks["zabbix"]
        
        return {
            "time": datetime.now().strftime("%H:%M:%S"),
            "inference": inf_res,
            "servers": zabbix_res,
            "alerts": [] # 告警逻辑前端处理或此处简化
        }

    @staticmethod
    async def check_db_sync():
        """按需：主从状态"""
        master_task = DBMonitor.get_basic_status(Config.MASTER, "master")
        slave_tasks = [DBMonitor.get_basic_status(s, "slave") for s in Config.SLAVES]
        
        return {
            "master": await master_task,
            "slaves": await asyncio.gather(*slave_tasks)
        }

    @staticmethod
    async def get_db_details(host_ip):
        """按需：获取单个数据库的详细指标（慢查询、锁等）"""
        # 从配置中找到对应的配置
        target = None
        if Config.MASTER['ip'] == host_ip:
            target = Config.MASTER
        else:
            for s in Config.SLAVES:
                if s['ip'] == host_ip:
                    target = s
                    break
        
        if target:
            return await DBMonitor.get_details(target)
        return {"error": "Unknown Host"}
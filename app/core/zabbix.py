import asyncio
from zabbix_utils import AsyncZabbixAPI
from app.config import Config
import structlog

logger = structlog.get_logger(__name__)

class ZabbixMonitor:
    @staticmethod
    async def get_hosts_metrics():
        if not Config.ZABBIX_ENABLED:
            return {}

        # 拼接 API URL
        api_url = f"{Config.ZABBIX_API_URL}/api_jsonrpc.php"
        
        try:
            # 1. 初始化并登录 API
            # client_session_kwargs={"connector": None} 用于禁用 SSL 验证(如果是内网)
            zapi = AsyncZabbixAPI(url=api_url) 
            
            await zapi.login(user=Config.ZABBIX_USER, password=Config.ZABBIX_PASSWORD)
            
            # 2. 获取 Host ID
            # 根据配置的 IP 列表查找 Zabbix 里的 Host ID
            hosts = await zapi.host.get(
                filter={"ip": Config.MONITOR_IPS},
                output=["hostid", "host", "name"],
                selectInterfaces=["ip"]
            )
            
            # 构建 IP -> HostID 映射
            ip_map = {}
            res = {ip: {"ip": ip, "status": "offline", "cpu": 0, "mem": 0, "disk": 0, "uptime": "-"} for ip in Config.MONITOR_IPS}
            
            for h in hosts:
                for interface in h['interfaces']:
                    if interface['ip'] in res:
                        ip_map[h['hostid']] = interface['ip']
                        res[interface['ip']]['status'] = 'online'
                        break
            
            if not ip_map:
                await zapi.logout()
                return res

            host_ids = list(ip_map.keys())

            # 3. 定义要查询的 Key
            # 确保你的 Zabbix Template 里有这些 Key
            keys_search = [
                "system.cpu.util",           # CPU
                "vm.memory.size[pused]",     # 内存%
                "vfs.fs.size[/,pused]",      # 磁盘% (根目录)
                "system.uptime"              # 运行时间
            ]

            # 4. 批量获取数据
            items = await zapi.item.get(
                hostids=host_ids,
                filter={"key_": keys_search},
                output=["itemid", "hostid", "key_", "lastvalue"],
                sortfield="name"
            )

            # 5. 填充数据
            for item in items:
                host_id = item['hostid']
                ip = ip_map.get(host_id)
                if not ip: continue

                key = item['key_']
                val = item['lastvalue']
                
                try:
                    if "system.cpu.util" in key:
                        res[ip]['cpu'] = round(float(val), 1)
                    
                    elif "vm.memory.size" in key:
                        res[ip]['mem'] = round(float(val), 1)
                    
                    elif "vfs.fs.size" in key:
                        res[ip]['disk'] = round(float(val), 1)
                    
                    elif "system.uptime" in key:
                        seconds = int(val)
                        days, remainder = divmod(seconds, 86400)
                        hours, _ = divmod(remainder, 3600)
                        res[ip]['uptime'] = f"{days}天{hours}小时"
                except (ValueError, TypeError):
                    pass

            await zapi.logout()
            return res

        except Exception as e:
            logger.error("zabbix_api_failed", error=str(e))
            # 发生错误时返回空数据，防止页面崩溃
            return {ip: {"ip": ip, "status": "err", "cpu": 0, "mem": 0, "disk": 0, "uptime": "-"} for ip in Config.MONITOR_IPS}
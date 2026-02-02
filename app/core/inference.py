import aiohttp
import asyncio
from app.core.utils import retry_async

# 全局复用 Session
_shared_session = None

async def get_session():
    global _shared_session
    if _shared_session is None or _shared_session.closed:
        connector = aiohttp.TCPConnector(limit=100, ttl_dns_cache=300)
        _shared_session = aiohttp.ClientSession(connector=connector)
    return _shared_session

class InferenceMonitor:
    @staticmethod
    @retry_async(retries=1)
    async def check_node(config):
        url = f"http://{config.ip}:{config.port}/health" 
        
        res = {
            "name": config.name, "url": f"{config.ip}:{config.port}",
            "status": "down", "latency": 0
        }
        
        start = asyncio.get_event_loop().time()
        
        # 1. 尝试 HTTP (使用共享 Session)
        try:
            session = await get_session()
            async with session.get(url, timeout=2) as response:
                duration = (asyncio.get_event_loop().time() - start) * 1000
                res["latency"] = int(duration)
                if response.status == 200:
                    res["status"] = "ready"
                    return res
                else:
                    res["status"] = f"http_{response.status}"
                    return res
        except:
            pass 
            
        # 2. 尝试 TCP Connect
        try:
            conn_start = asyncio.get_event_loop().time()
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(config.ip, config.port), timeout=2
            )
            # TCP 建立连接即视为通
            latency = (asyncio.get_event_loop().time() - conn_start) * 1000
            res["latency"] = int(latency)
            res["status"] = "tcp_ok" 
            
            writer.close()
            await writer.wait_closed()
        except:
            res["status"] = "offline"
            
        return res
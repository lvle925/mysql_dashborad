import time
import asyncio
from datetime import datetime
from functools import wraps

class TimedCache:
    def __init__(self, ttl=30):
        self.cache = {}
        self.ttl = ttl
    
    def get(self, key):
        if key in self.cache:
            val, ts = self.cache[key]
            if (datetime.now() - ts).seconds < self.ttl:
                return val
        return None
    
    def set(self, key, value):
        self.cache[key] = (value, datetime.now())

# 全局缓存
cache = TimedCache(ttl=15)

def retry_async(retries=2, delay=1):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_err = None
            for i in range(retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_err = e
                    if i < retries:
                        await asyncio.sleep(delay)
            # 记录错误但不崩溃，返回None或默认值由调用者处理
            print(f"[Warn] {func.__name__} failed: {last_err}")
            return None 
        return wrapper
    return decorator
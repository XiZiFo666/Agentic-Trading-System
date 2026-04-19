import os
import requests
from requests_cache import CacheMixin, SQLiteCache
from requests_ratelimiter import LimiterMixin


# 组装一个同时具备“缓存”和“限流”功能的超级 Session
class CachedLimiterSession(CacheMixin, LimiterMixin, requests.Session):
    pass


# 单例模式，确保所有 Agent 复用同一个排队通道
_session = None


def get_yf_session():
    global _session
    if _session is None:
        # 确保缓存目录存在
        os.makedirs("cache", exist_ok=True)

        # 【极简配置】最新版的库支持直接传入 per_second 即可！
        _session = CachedLimiterSession(
            per_second=2,  # 核心护盾：每秒最多 2 次请求，自动排队
            backend=SQLiteCache("cache/yfinance_cache.sqlite"),  # 缓存存入本地
            expire_after=86400  # 缓存有效期 24 小时
        )

        # 完美浏览器伪装
        _session.headers[
            'User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

    return _session
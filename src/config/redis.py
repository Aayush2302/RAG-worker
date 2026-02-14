# config/redis.py
from redis import Redis
from src.config.env import env
import ssl

# Create Redis connection for BullMQ
# IMPORTANT: python-bullmq uses this connection
redis_client = Redis.from_url(
    env.REDIS_URL,
    decode_responses=False,  # BullMQ requires binary mode
    max_connections=50,
    socket_keepalive=True,
    socket_connect_timeout=5,
    retry_on_timeout=True,
    health_check_interval=30,
    # TLS configuration for Upstash/remote Redis
    ssl_cert_reqs=ssl.CERT_NONE if env.REDIS_URL.startswith('rediss://') else None
)

print("✅ Redis client initialized for BullMQ")

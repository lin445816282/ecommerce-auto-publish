"""重试 & 熔断工具"""
import time
import functools
from datetime import datetime, timedelta
from config.settings import MAX_RETRY, RETRY_DELAY, CIRCUIT_BREAKER_THRESHOLD, CIRCUIT_BREAKER_TIMEOUT


class CircuitBreaker:
    """熔断器：连续失败N次后熔断，超时后恢复"""

    def __init__(self, name: str, threshold: int = None, timeout: int = None):
        self.name = name
        self.threshold = threshold or CIRCUIT_BREAKER_THRESHOLD
        self.timeout = timeout or CIRCUIT_BREAKER_TIMEOUT
        self.fail_count = 0
        self.last_fail_time = None
        self.open = False

    def call(self, func, *args, **kwargs):
        if self.open:
            if datetime.now() - self.last_fail_time > timedelta(seconds=self.timeout):
                self.open = False
                self.fail_count = 0
                print(f"[Breaker:{self.name}] 熔断恢复，重试")
            else:
                raise Exception(f"[Breaker:{self.name}] 熔断中，拒绝调用")

        try:
            result = func(*args, **kwargs)
            self.fail_count = 0
            return result
        except Exception as e:
            self.fail_count += 1
            self.last_fail_time = datetime.now()
            if self.fail_count >= self.threshold:
                self.open = True
                print(f"[Breaker:{self.name}] 连续失败{self.fail_count}次，触发熔断")
            raise e


def retry_with_backoff(max_retry: int = None):
    """指数退避重试装饰器"""
    max_r = max_retry or MAX_RETRY

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_err = None
            for attempt in range(max_r + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_err = e
                    if attempt < max_r:
                        delay = RETRY_DELAY[min(attempt, len(RETRY_DELAY) - 1)]
                        print(f"[Retry] {func.__name__} 第{attempt+1}次重试，等待{delay}s: {e}")
                        time.sleep(delay)
            raise last_err
        return wrapper
    return decorator


print("[RetryUtils] CircuitBreaker & retry_with_backoff ready.")

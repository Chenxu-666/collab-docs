"""进程内滑动窗口限流器（防暴力破解）。生产多实例部署时可替换为 Redis 实现。"""
import threading
import time
from collections import defaultdict, deque

from .config import RATE_LIMIT_LOCK, RATE_LIMIT_MAX_ATTEMPTS, RATE_LIMIT_WINDOW


class SlidingWindowLimiter:
    def __init__(self, max_attempts: int, window_seconds: int, lock_seconds: int):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.lock_seconds = lock_seconds
        self._lock = threading.Lock()
        self._attempts: dict[str, deque] = defaultdict(deque)
        self._locked_until: dict[str, float] = {}

    def is_locked(self, key: str) -> tuple[bool, int]:
        """返回 (是否锁定, 剩余锁定秒数)。"""
        remain = self._locked_until.get(key, 0.0) - time.time()
        if remain > 0:
            return True, int(remain) + 1
        return False, 0

    def record_failure(self, key: str) -> bool:
        """记录一次失败，返回是否触发了锁定。"""
        now = time.time()
        with self._lock:
            q = self._attempts[key]
            q.append(now)
            while q and q[0] < now - self.window_seconds:
                q.popleft()
            if len(q) >= self.max_attempts:
                self._locked_until[key] = now + self.lock_seconds
                q.clear()
                return True
        return False

    def reset(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)
            self._locked_until.pop(key, None)


# 登录：5 分钟内失败 5 次 → 锁定 15 分钟
login_limiter = SlidingWindowLimiter(
    max_attempts=RATE_LIMIT_MAX_ATTEMPTS,
    window_seconds=RATE_LIMIT_WINDOW,
    lock_seconds=RATE_LIMIT_LOCK,
)

# 注册：每小时最多 20 次（按 IP）
register_limiter = SlidingWindowLimiter(max_attempts=20, window_seconds=3600, lock_seconds=3600)

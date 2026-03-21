#!/usr/bin/env python3
"""监控器"""

import json
import time
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class TokenUsageRecord:
    timestamp: str
    operation: str
    tokens_used: int
    context: str

class TokenMonitor:
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.usage_file = self.data_dir / "usage_history.json"
        self.usage_history: List[TokenUsageRecord] = []
        self.daily_budget = 10000
        self.hourly_budget = 2000
        self._load_history()

    def _load_history(self):
        if self.usage_file.exists():
            data = json.loads(self.usage_file.read_text())
            self.usage_history = [TokenUsageRecord(**r) for r in data]

    def _save_history(self):
        cutoff = datetime.now() - timedelta(days=30)
        recent = [asdict(r) for r in self.usage_history
                  if datetime.fromisoformat(r.timestamp) > cutoff]
        self.usage_file.write_text(json.dumps(recent, indent=2))

    def record_usage(self, operation: str, tokens: int, context: str = ""):
        self.usage_history.append(TokenUsageRecord(
            timestamp=datetime.now().isoformat(),
            operation=operation,
            tokens_used=tokens,
            context=context
        ))
        self._save_history()
        self._check_alerts()

    def _get_usage(self, period: timedelta) -> int:
        cutoff = datetime.now() - period
        return sum(r.tokens_used for r in self.usage_history
                   if datetime.fromisoformat(r.timestamp) > cutoff)

    def _check_alerts(self):
        hour = self._get_usage(timedelta(hours=1))
        day = self._get_usage(timedelta(days=1))

        if hour > self.hourly_budget:
            print(f"⚠️ 小时预算超支: {hour} > {self.hourly_budget}")
        if day > self.daily_budget:
            print(f"⚠️ 日预算超支: {day} > {self.daily_budget}")

    def get_stats(self, period: str = "day") -> Dict:
        delta = {"hour": timedelta(hours=1), "day": timedelta(days=1), "week": timedelta(weeks=1)}.get(period, timedelta(days=1))
        usage = self._get_usage(delta)
        ops = len([r for r in self.usage_history if datetime.fromisoformat(r.timestamp) > datetime.now() - delta])

        return {
            "period": period, "total_tokens": usage, "operations": ops,
            "avg_per_op": usage // ops if ops else 0,
            "budget": {"daily": self.daily_budget, "used_today": self._get_usage(timedelta(days=1))}
        }

    def watch(self, path: str, interval: int = 60):
        print(f"监控 {path} (每{interval}秒)")
        try:
            while True:
                time.sleep(interval)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 运行中...")
        except KeyboardInterrupt:
            print("停止监控")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='监控器')
    parser.add_argument('--stats', action='store_true', help='显示统计')
    parser.add_argument('--watch', metavar='PATH', help='监控路径')
    args = parser.parse_args()

    monitor = TokenMonitor()

    if args.stats:
        print(json.dumps(monitor.get_stats(), indent=2))
    elif args.watch:
        monitor.watch(args.watch)
    else:
        print("使用 --stats 或 --watch PATH")

if __name__ == "__main__":
    main()

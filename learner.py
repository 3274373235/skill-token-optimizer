#!/usr/bin/env python3
"""学习器"""

import json
import hashlib
import re
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict

@dataclass
class OptimizationCase:
    case_id: str
    original: str
    optimized: str
    strategy: str
    context: str
    success_rating: float
    timestamp: str
    original_tokens: int
    optimized_tokens: int

class TokenOptimizationLearner:
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.cases_file = self.data_dir / "optimization_cases.json"
        self.cases: list = []
        self._load_data()

    def _load_data(self):
        if self.cases_file.exists():
            data = json.loads(self.cases_file.read_text())
            self.cases = [OptimizationCase(**c) for c in data]

    def _save_data(self):
        self.cases_file.write_text(json.dumps([asdict(c) for c in self.cases], indent=2, ensure_ascii=False))

    def learn_from_case(self, original: str, optimized: str, strategy: str,
                       context: str = "", success_rating: float = 1.0) -> str:
        case_id = hashlib.md5(f"{original}{optimized}{datetime.now()}".encode()).hexdigest()[:12]

        case = OptimizationCase(
            case_id=case_id,
            original=original[:500],
            optimized=optimized[:500],
            strategy=strategy,
            context=context,
            success_rating=success_rating,
            timestamp=datetime.now().isoformat(),
            original_tokens=len(original) // 4,
            optimized_tokens=len(optimized) // 4
        )

        self.cases.append(case)
        self._save_data()
        return case_id

    def suggest_optimizations(self, text: str) -> list:
        if len(self.cases) < 5:
            return []

        suggestions = []
        for case in self.cases[-10:]:
            if self._is_similar(text, case.original):
                suggestions.append({
                    "strategy": case.strategy,
                    "confidence": case.success_rating,
                    "example_saving": case.original_tokens - case.optimized_tokens
                })
        return suggestions

    def _is_similar(self, text1: str, text2: str) -> bool:
        words1 = set(re.findall(r'\b\w+\b', text1.lower()))
        words2 = set(re.findall(r'\b\w+\b', text2.lower()))
        if not words1 or not words2:
            return False
        return len(words1 & words2) / max(len(words1), len(words2)) > 0.3

    def generate_learning_report(self) -> dict:
        if not self.cases:
            return {"status": "尚无足够数据"}

        total_saved = sum(c.original_tokens - c.optimized_tokens for c in self.cases)
        avg_rating = sum(c.success_rating for c in self.cases) / len(self.cases)

        strategies = {}
        for c in self.cases:
            strategies[c.strategy] = strategies.get(c.strategy, 0) + 1

        return {
            "cases_count": len(self.cases),
            "total_saved": total_saved,
            "avg_success": round(avg_rating, 2),
            "top_strategies": sorted(strategies.items(), key=lambda x: x[1], reverse=True)[:5]
        }

def main():
    import argparse
    parser = argparse.ArgumentParser(description='学习器')
    parser.add_argument('--report', action='store_true', help='生成报告')
    args = parser.parse_args()

    learner = TokenOptimizationLearner()

    if args.report:
        report = learner.generate_learning_report()
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"已学习案例: {len(learner.cases)}")

if __name__ == "__main__":
    main()

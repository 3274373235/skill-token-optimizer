#!/usr/bin/env python3
"""学习器 v1.2 - 支持模式提取与应用"""

import json
import hashlib
import re
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict

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
        self.patterns_file = self.data_dir.parent / "patterns" / "learned_patterns.json"
        self.patterns_file.parent.mkdir(exist_ok=True)
        self.cases: List[OptimizationCase] = []
        self._load_data()
        self._load_patterns()

    def _load_data(self):
        if self.cases_file.exists():
            data = json.loads(self.cases_file.read_text())
            self.cases = [OptimizationCase(**c) for c in data]

    def _save_data(self):
        self.cases_file.write_text(json.dumps([asdict(c) for c in self.cases], indent=2, ensure_ascii=False))

    def _load_patterns(self):
        if self.patterns_file.exists():
            self.patterns = json.loads(self.patterns_file.read_text())
        else:
            self.patterns = {"patterns": []}

    def _save_patterns(self):
        self.patterns_file.write_text(json.dumps(self.patterns, indent=2, ensure_ascii=False))

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
        # 尝试提取模式
        self._extract_patterns_from_case(original, optimized, strategy, success_rating)
        return case_id

    def _extract_patterns_from_case(self, original: str, optimized: str, strategy: str, rating: float):
        """从成功案例中自动提取通用替换模式（如删除特定冗余词）"""
        if rating < 0.8 or len(original) - len(optimized) < 5:
            return
        # 寻找原文本中删除的连续片段
        # 简单启发式：找出 original 中有但 optimized 中没有的长词汇
        orig_words = set(re.findall(r'[\u4e00-\u9fff]+', original))
        opt_words = set(re.findall(r'[\u4e00-\u9fff]+', optimized))
        removed = orig_words - opt_words
        for word in removed:
            if len(word) >= 2 and word not in ["的", "了", "吗", "呢"]:
                pattern = word
                replacement = ""
                # 避免重复添加相同模式
                existing = any(p["pattern"] == pattern for p in self.patterns["patterns"])
                if not existing:
                    self.patterns["patterns"].append({
                        "pattern": pattern,
                        "replacement": replacement,
                        "confidence": rating,
                        "source_strategy": strategy,
                        "frequency": 1
                    })
        # 合并重复的模式
        merged = {}
        for p in self.patterns["patterns"]:
            key = p["pattern"]
            if key in merged:
                merged[key]["frequency"] += 1
                merged[key]["confidence"] = max(merged[key]["confidence"], p["confidence"])
            else:
                merged[key] = p.copy()
        self.patterns["patterns"] = list(merged.values())
        self._save_patterns()

    def suggest_optimizations(self, text: str, file_path: str = "") -> List[Dict]:
        """返回优化建议（基于历史案例和学习模式）"""
        suggestions = []
        # 1. 基于模式库的替换建议
        for pat in self.patterns.get("patterns", []):
            if pat["confidence"] > 0.7 and re.search(pat["pattern"], text):
                suggestions.append({
                    "strategy": pat.get("source_strategy", "learned_pattern"),
                    "pattern_key": pat["pattern"],
                    "replacement": pat["replacement"],
                    "confidence": pat["confidence"],
                    "frequency": pat.get("frequency", 1)
                })
        # 2. 基于相似案例的压缩建议（保留原有逻辑）
        if len(self.cases) >= 5:
            for case in self.cases[-10:]:
                if self._is_similar(text, case.original):
                    suggestions.append({
                        "strategy": case.strategy,
                        "confidence": case.success_rating,
                        "example_saving": case.original_tokens - case.optimized_tokens,
                        "pattern_key": None
                    })
        # 去重
        unique = []
        seen = set()
        for s in suggestions:
            key = f"{s['strategy']}_{s.get('pattern_key', '')}"
            if key not in seen:
                seen.add(key)
                unique.append(s)
        return unique

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
            "patterns_count": len(self.patterns.get("patterns", [])),
            "total_saved": total_saved,
            "avg_success": round(avg_rating, 2),
            "top_strategies": sorted(strategies.items(), key=lambda x: x[1], reverse=True)[:5]
        }

def main():
    import argparse
    parser = argparse.ArgumentParser(description='学习器 v1.2')
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

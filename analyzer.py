#!/usr/bin/env python3
"""Token分析器"""

import json
import re
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class TokenAnalysis:
    file_path: str
    total_tokens: int
    prompt_tokens: int
    code_tokens: int
    comment_tokens: int
    whitespace_tokens: float
    waste_score: float
    suggestions: list

class TokenAnalyzer:
    def __init__(self):
        self.patterns = self._load_patterns()

    def _load_patterns(self) -> dict:
        f = Path(__file__).parent / "patterns" / "learned_patterns.json"
        return json.loads(f.read_text()) if f.exists() else {"waste_patterns": []}

    def estimate_tokens(self, text: str) -> int:
        chinese = len(re.findall(r'[\u4e00-\u9fff]', text))
        return int(chinese / 2 + (len(text) - chinese) / 4)

    def analyze_file(self, file_path: str) -> TokenAnalysis:
        path = Path(file_path)
        content = path.read_text(encoding='utf-8')

        if path.suffix in ['.md', '.txt']:
            return self._analyze_prompt(content, file_path)
        elif path.suffix in ['.py', '.js', '.ts']:
            return self._analyze_code(content, file_path)
        return self._analyze_generic(content, file_path)

    def _analyze_prompt(self, content: str, file_path: str) -> TokenAnalysis:
        total = self.estimate_tokens(content)
        suggestions, waste = [], 0

        patterns = [
            (r'非常|特别|十分|极其', "可删除冗余程度副词", 2),
            (r'重要的|关键的|核心', "可简化", 2),
        ]

        for p, s, cost in patterns:
            matches = re.findall(p, content)
            if matches:
                suggestions.append({"type": "冗余", "count": len(matches), "suggestion": s, "saving": len(matches) * cost})
                waste += len(matches) * 2

        return TokenAnalysis(file_path, total, total, 0, 0, content.count('\n') * 0.5, min(waste, 100), suggestions)

    def _analyze_code(self, content: str, file_path: str) -> TokenAnalysis:
        total = self.estimate_tokens(content)
        suggestions, waste = [], 0

        lines = content.split('\n')
        dup = {l.strip() for l in lines if len(l.strip()) > 10}
        if len(dup) < len([l for l in lines if len(l.strip()) > 10]) * 0.9:
            suggestions.append({"type": "重复代码", "suggestion": "提取函数"})
            waste += 10

        imports = re.findall(r'^(?:import|from)\s+(\w+)', content, re.MULTILINE)
        if len(imports) > 15:
            suggestions.append({"type": "导入过多", "suggestion": "按需导入"})
            waste += 5

        return TokenAnalysis(file_path, total, 0, total, 0, 0, min(waste, 100), suggestions)

    def _analyze_generic(self, content: str, file_path: str) -> TokenAnalysis:
        return TokenAnalysis(file_path, self.estimate_tokens(content), 0, 0, 0, 0, 0, [])

    def analyze_directory(self, dir_path: str) -> list:
        return [self.analyze_file(str(f)) for f in Path(dir_path).rglob('*')
                if f.is_file() and f.suffix in ['.md', '.py', '.js']]

    def generate_report(self, results: list) -> dict:
        total = sum(r.total_tokens for r in results)
        waste = sum(r.waste_score for r in results) / len(results) if results else 0
        saving = sum(s.get("saving", 0) for r in results for s in r.suggestions)

        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "files": len(results), "total_tokens": total,
                "waste_score": round(waste, 2), "saving": saving,
                "saving_pct": round(saving / total * 100, 2) if total else 0
            },
            "details": [asdict(r) for r in results]
        }

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Token分析器')
    parser.add_argument('path', help='文件或目录')
    parser.add_argument('-o', '--output', help='输出报告')
    args = parser.parse_args()

    analyzer = TokenAnalyzer()
    path = Path(args.path)
    results = [analyzer.analyze_file(str(path))] if path.is_file() else analyzer.analyze_directory(str(path))
    report = analyzer.generate_report(results)

    print(f"文件: {report['summary']['files']}, Token: {report['summary']['total_tokens']:,}")
    print(f"浪费: {report['summary']['waste_score']:.1f}/100, 可节省: {report['summary']['saving']:,}")

    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""提示词压缩器 - 保留语义的同时减少Token使用 v1.2"""

import re
import json
from pathlib import Path
from dataclasses import dataclass

@dataclass
class CompressionResult:
    original: str
    compressed: str
    original_tokens: int
    compressed_tokens: int
    strategy_used: list
    confidence: float

class PromptCompressor:
    """提示词压缩器 - 支持学习模式动态应用"""

    def __init__(self, patterns_file: str = "./patterns/learned_patterns.json"):
        self.patterns_file = Path(patterns_file)
        self.learned_patterns = self._load_learned_patterns()
        self.strategies = [
            self._remove_redundant,
            self._simplify_courtesy,
            self._compress_lists,
            self._merge_repeated_phrases,
            self._shorten_explanations,
            self._apply_learned_patterns,
        ]

    def _load_learned_patterns(self):
        if self.patterns_file.exists():
            data = json.loads(self.patterns_file.read_text())
            return data.get("patterns", [])
        return []

    def estimate_tokens(self, text: str) -> int:
        chinese = len(re.findall(r'[\u4e00-\u9fff]', text))
        return int(chinese / 2 + (len(text) - chinese) / 4)

    def compress(self, prompt: str, aggressive: bool = False) -> CompressionResult:
        original = prompt
        compressed = prompt
        strategies_used = []

        for strategy in self.strategies:
            new_text, name, applied = strategy(compressed, aggressive)
            if applied:
                compressed = new_text
                strategies_used.append(name)

        return CompressionResult(
            original=original,
            compressed=compressed,
            original_tokens=self.estimate_tokens(original),
            compressed_tokens=self.estimate_tokens(compressed),
            strategy_used=strategies_used,
            confidence=0.9 if not aggressive else 0.75
        )

    def _apply_patterns(self, text: str, patterns: list) -> tuple:
        new_text, applied = text, False
        for p, r in patterns:
            if re.search(p, new_text):
                new_text = re.sub(p, r, new_text)
                applied = True
        return new_text, applied

    def _remove_redundant(self, text: str, aggressive: bool) -> tuple:
        patterns = [
            (r'非常|特别|十分|极其', ''),
            (r'很大的|大量的', '多'),
            (r'很小的|少量的', '少'),
            (r'很好的|优秀的', '好'),
            (r'非常地|特别地', ''),
            (r'基本上可以说|基本上', ''),
        ]
        if aggressive:
            patterns.extend([(r'很|挺|蛮', ''), (r'也许|可能|大概', '')])
        new_text, applied = self._apply_patterns(text, patterns)
        return new_text, "移除冗余", applied

    def _simplify_courtesy(self, text: str, aggressive: bool) -> tuple:
        patterns = [(r'请|谢谢|感谢|麻烦您', ''), (r'如果可能|如果可以|在不影响的情况下', '')]
        if aggressive:
            patterns.append((r'您', '你'))
        new_text, applied = self._apply_patterns(text, patterns)
        return re.sub(r'\s+', ' ', new_text).strip(), "简化客套", applied

    def _compress_lists(self, text: str, aggressive: bool) -> tuple:
        items = re.findall(r'(?:^|\n)(?:\d+[.．、]|[-•*])\s*(.+?)(?=\n|$)', text, re.MULTILINE)
        if len(items) < 3:
            return text, "列表压缩", False

        # 寻找公共前缀
        prefix = items[0]
        for s in items[1:]:
            while not s.startswith(prefix):
                prefix = prefix[:-1]
                if not prefix:
                    return text, "列表压缩", False
        if len(prefix) > 5:
            new_items = [i[len(prefix):].strip() for i in items]
            # 保留原行号格式仅用于定位删除
            new_text = re.sub(r'(?:^|\n)(?:\d+[.．、]|[-•*])\s*.+?(?=\n|$)', '', text, count=len(items), flags=re.MULTILINE)
            return new_text.strip() + f"\n{prefix}: " + " | ".join(new_items), "列表压缩", True
        return text, "列表压缩", False

    def _merge_repeated_phrases(self, text: str, aggressive: bool) -> tuple:
        """合并连续重复的短语（如 '非常重要非常重要' -> '非常重要'）"""
        new_text = re.sub(r'(\S{2,}?)\1+', r'\1', text)
        return new_text, "合并重复短语", new_text != text

    def _shorten_explanations(self, text: str, aggressive: bool) -> tuple:
        """缩短冗长解释性语句"""
        patterns = [
            (r'也就是说[,，]', '即'),
            (r'换句话说[,，]', '即'),
            (r'需要注意的是[,，]', '注意'),
            (r'在这里我们[,，]', ''),
            (r'对于.*?而言[,，]', ''),
        ]
        new_text, applied = self._apply_patterns(text, patterns)
        return new_text, "缩短解释", applied

    def _apply_learned_patterns(self, text: str, aggressive: bool) -> tuple:
        """应用从历史案例中学到的替换模式"""
        if not self.learned_patterns:
            return text, "学习模式", False
        new_text = text
        applied = False
        for pat in self.learned_patterns:
            if pat.get("confidence", 0) > 0.7:
                pattern = pat["pattern"]
                replacement = pat["replacement"]
                if re.search(pattern, new_text):
                    new_text = re.sub(pattern, replacement, new_text)
                    applied = True
        return new_text, "学习模式", applied

    def smart_compress(self, prompt: str, target: int = None, budget_remaining: float = 1.0) -> CompressionResult:
        """预算感知压缩：预算紧张时使用更激进的策略"""
        if target and self.estimate_tokens(prompt) <= target:
            return self.compress(prompt, aggressive=False)
        aggressive = (budget_remaining < 0.3)  # 剩余预算不足30%时启用激进压缩
        return self.compress(prompt, aggressive=aggressive)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='提示词压缩器 v1.2')
    parser.add_argument('prompt', help='要压缩的提示词')
    parser.add_argument('-a', '--aggressive', action='store_true')
    args = parser.parse_args()

    comp = PromptCompressor()
    result = comp.compress(args.prompt, args.aggressive)

    print(f"原始: {result.original_tokens} → 压缩后: {result.compressed_tokens} (节省 {result.original_tokens - result.compressed_tokens} tokens)")
    print(f"策略: {', '.join(result.strategy_used)}")
    print(f"结果: {result.compressed[:200]}...")

if __name__ == "__main__":
    main()

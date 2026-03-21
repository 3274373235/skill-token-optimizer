#!/usr/bin/env python3
"""提示词压缩器 - 保留语义的同时减少Token使用"""

import re
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
    """提示词压缩器"""

    CHARS_PER_TOKEN = 4
    CHINESE_CHARS_PER_TOKEN = 2

    SYNONYMS = {
        "非常重要": "关键", "非常重要地": "务必", "请确保": "确保",
        "请保证": "保证", "非常重要的": "核心", "关键的": "核心",
        "详细的": "详", "详细地": "详述", "一步一步地": "逐步",
        "首先": "1.", "其次": "2.", "然后": "3.", "最后": "4.",
        "例如": "如", "比如": "如", "等等": "等", "以及": "及",
    }

    def __init__(self):
        self.strategies = [
            self._remove_redundant,
            self._simplify_courtesy,
            self._compress_lists,
        ]

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
            (r'非常|特别|十分|极其', ''), (r'很大的|大量的', '多'),
            (r'很小的|少量的', '少'), (r'很好的|优秀的', '好'),
        ]
        new_text, applied = self._apply_patterns(text, patterns)
        return new_text, "移除冗余", applied

    def _simplify_courtesy(self, text: str, aggressive: bool) -> tuple:
        patterns = [(r'请|谢谢|感谢', ''), (r'如果可能|如果可以', '')]
        new_text, applied = self._apply_patterns(text, patterns)
        return re.sub(r'\s+', ' ', new_text).strip(), "简化客套", applied

    def _compress_lists(self, text: str, aggressive: bool) -> tuple:
        items = re.findall(r'(?:^|\n)(?:\d+[.．、]|[-•*])\s*(.+?)(?=\n|$)', text)
        if len(items) < 3:
            return text,"列表压缩",False

        prefix = items[0]
        for s in items[1:]:
            while not s.startswith(prefix):
                prefix = prefix[:-1]
                if not prefix: return text,"列表压缩",False

        if len(prefix) > 5:
            new_items = [i[len(prefix):].strip() for i in items]
            new_text = re.sub(r'(?:^|\n)(?:\d+[.．、]|[-•*])\s*.+?(?=\n|$)', '', text, count=len(items))
            return new_text.strip() + f"\n{prefix}: " + " | ".join(new_items), "列表压缩", True

        return text,"列表压缩",False

    def smart_compress(self, prompt: str, target: int = None) -> CompressionResult:
        result = self.compress(prompt, aggressive=False)
        if target and result.compressed_tokens > target:
            result = self.compress(prompt, aggressive=True)
        return result

def main():
    import argparse
    parser = argparse.ArgumentParser(description='提示词压缩器')
    parser.add_argument('prompt', help='要压缩的提示词')
    parser.add_argument('-a', '--aggressive', action='store_true')
    args = parser.parse_args()

    comp = PromptCompressor()
    result = comp.compress(args.prompt, args.aggressive)

    print(f"原始: {result.original_tokens} → 压缩后: {result.compressed_tokens}")
    print(f"策略: {', '.join(result.strategy_used)}")
    print(f"结果: {result.compressed[:100]}...")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
测试套件 v1.2 - 验证Token优化器效果（覆盖新特性）
"""

import sys
import unittest
import tempfile
import json
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from compressor import PromptCompressor
from analyzer import TokenAnalyzer
from learner import TokenOptimizationLearner
from auto_optimize import TokenAutoOptimizer
from monitor import TokenMonitor


class TestPromptCompressorV12(unittest.TestCase):
    """测试提示词压缩器 v1.2 新特性"""

    def setUp(self):
        # 使用临时目录存放学习模式，避免污染真实数据
        self.temp_dir = tempfile.TemporaryDirectory()
        patterns_file = Path(self.temp_dir.name) / "patterns" / "learned_patterns.json"
        patterns_file.parent.mkdir(parents=True, exist_ok=True)
        self.compressor = PromptCompressor(patterns_file=str(patterns_file))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_basic_compression(self):
        prompt = "这是一个非常重要的任务，请你非常仔细地完成。"
        result = self.compressor.compress(prompt)
        self.assertLess(result.compressed_tokens, result.original_tokens)
        self.assertGreater(result.confidence, 0.5)

    def test_aggressive_compression(self):
        prompt = "请确保你非常仔细地检查每一个非常重要的细节，非常感谢你的帮助。"
        result_normal = self.compressor.compress(prompt, aggressive=False)
        result_aggressive = self.compressor.compress(prompt, aggressive=True)
        self.assertLessEqual(result_aggressive.compressed_tokens, result_normal.compressed_tokens)

    def test_list_compression(self):
        prompt = """任务列表：
1. 完成数据清洗
2. 完成数据清洗
3. 完成数据清洗
4. 完成数据清洗
5. 完成数据清洗"""
        result = self.compressor.compress(prompt)
        self.assertIn("完成数据清洗:", result.compressed)  # 应合并为公共前缀形式
        self.assertLess(result.compressed_tokens, result.original_tokens)

    def test_merge_repeated_phrases(self):
        prompt = "非常重要非常重要请仔细仔细检查"
        result = self.compressor.compress(prompt)
        # 重复短语应被合并
        self.assertNotIn("非常重要非常重要", result.compressed)
        self.assertLess(result.compressed_tokens, result.original_tokens)

    def test_shorten_explanations(self):
        prompt = "也就是说，我们需要处理这个问题。需要注意的是，这里很关键。"
        result = self.compressor.compress(prompt)
        self.assertNotIn("也就是说", result.compressed)
        self.assertNotIn("需要注意的是", result.compressed)

    def test_budget_aware_compress(self):
        prompt = "很长的提示词" * 50
        # 剩余预算充足（>0.3）应使用普通压缩
        result_normal = self.compressor.smart_compress(prompt, budget_remaining=0.8)
        # 剩余预算紧张（<0.3）应使用激进压缩
        result_aggressive = self.compressor.smart_compress(prompt, budget_remaining=0.2)
        self.assertLessEqual(result_aggressive.compressed_tokens, result_normal.compressed_tokens)


class TestTokenAnalyzerV12(unittest.TestCase):
    """测试Token分析器 v1.2（增强浪费检测）"""

    def setUp(self):
        self.analyzer = TokenAnalyzer()

    def test_estimate_tokens(self):
        text = "这是一个测试文本，用于验证Token估算功能。"
        tokens = self.analyzer.estimate_tokens(text)
        # 仅检查合法性：应大于0且小于字符数（因为中文1.5字符/token）
        self.assertGreater(tokens, 0)
        self.assertLess(tokens, len(text) * 2)

    def test_analyze_prompt_with_redundancy(self):
        prompt = """基于以上分析，为了更好地完成任务，也就是说，请仔细检查重复了三次的说明。非常感谢！"""
        result = self.analyzer._analyze_prompt(prompt, "test.md")
        self.assertGreater(result.total_tokens, 0)
        # 应检测到冗余模式（“基于以上分析”、“也就是说”等）
        pattern_types = [s.get("type") for s in result.suggestions]
        self.assertTrue(any("冗余" in t for t in pattern_types), "应检测到冗余模式")

    def test_analyze_code_with_dead_code(self):
        code = """
import os
import sys
import json
import re
import math   # 未使用
def foo():
    x = 1
    x = 1   # 重复行
    return x
"""
        result = self.analyzer._analyze_code(code, "test.py")
        # 应检测到导入过多和重复代码
        suggestions = result.suggestions
        self.assertTrue(any(s.get("type") == "导入过多" for s in suggestions) or
                        any(s.get("type") == "重复代码" for s in suggestions))


class TestLearnerV12(unittest.TestCase):
    """测试学习器 v1.2（模式提取与持久化）"""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.learner = TokenOptimizationLearner(data_dir=self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_learn_from_case_and_extract_pattern(self):
        original = "这是一个非常非常重要的关键点"
        optimized = "这是一个关键点"
        self.learner.learn_from_case(original, optimized, "remove_redundant", success_rating=0.9)
        # 验证模式被提取并保存
        patterns_file = Path(self.temp_dir.name).parent / "patterns" / "learned_patterns.json"
        self.assertTrue(patterns_file.exists())
        data = json.loads(patterns_file.read_text())
        patterns = data.get("patterns", [])
        # 应提取到 "非常非常重要" 或类似短语的模式
        self.assertTrue(any("非常" in p["pattern"] for p in patterns), "未提取到预期模式")

    def test_suggest_optimizations_with_patterns(self):
        self.learner.learn_from_case("请仔细检查", "检查", "remove_courtesy", success_rating=0.95)
        suggestions = self.learner.suggest_optimizations("请仔细查看数据", "test.md")
        self.assertIsInstance(suggestions, list)
        self.assertGreater(len(suggestions), 0, "应返回基于模式的建议")
        self.assertIn("pattern_key", suggestions[0])


class TestAutoOptimizerV12(unittest.TestCase):
    """测试自动优化器 v1.2（预算感知、工作流优化）"""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.skill_dir = Path(self.temp_dir.name) / "test_skill"
        self.skill_dir.mkdir()
        # 创建测试文件
        (self.skill_dir / "README.md").write_text("这是一个非常重要的提示词，请你非常仔细地完成。")
        (self.skill_dir / "script.py").write_text("import os\nimport sys\nprint('hello')\nimport math\n")
        self.optimizer = TokenAutoOptimizer(str(self.skill_dir), backup=False)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_optimize_skill_with_budget_aware(self):
        report = self.optimizer.optimize_skill(auto_fix=True, budget_aware=True)
        self.assertEqual(report["status"], "success")
        self.assertGreater(report["summary"]["optimizations_applied"], 0)
        # 验证文件确实被修改
        new_content = (self.skill_dir / "README.md").read_text()
        self.assertNotIn("非常非常", new_content)


class TestMonitorV12(unittest.TestCase):
    """测试监控器 v1.2（联动优化器）"""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.monitor = TokenMonitor(data_dir=self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_should_compress_aggressively(self):
        # 未超过预算时不应激进
        self.assertFalse(self.monitor.should_compress_aggressively())
        # 模拟接近预算
        for _ in range(80):
            self.monitor.record_usage("test", 100)  # 80*100=8000，接近日预算10000
        self.assertTrue(self.monitor.should_compress_aggressively())


def run_tests():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestPromptCompressorV12))
    suite.addTests(loader.loadTestsFromTestCase(TestTokenAnalyzerV12))
    suite.addTests(loader.loadTestsFromTestCase(TestLearnerV12))
    suite.addTests(loader.loadTestsFromTestCase(TestAutoOptimizerV12))
    suite.addTests(loader.loadTestsFromTestCase(TestMonitorV12))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

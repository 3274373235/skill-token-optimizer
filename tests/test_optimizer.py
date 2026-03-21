#!/usr/bin/env python3
"""
测试套件 - 验证Token优化器效果
"""

import sys
import unittest
import tempfile
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from compressor import PromptCompressor
from analyzer import TokenAnalyzer
from learner import TokenOptimizationLearner


class TestPromptCompressor(unittest.TestCase):
    """测试提示词压缩器"""
    
    def setUp(self):
        self.compressor = PromptCompressor()
    
    def test_basic_compression(self):
        """测试基本压缩"""
        prompt = "这是一个非常重要的任务，请你非常仔细地完成。"
        result = self.compressor.compress(prompt)
        
        self.assertLess(result.compressed_tokens, result.original_tokens)
        self.assertGreater(result.confidence, 0.5)
    
    def test_aggressive_compression(self):
        """测试激进压缩"""
        prompt = "请确保你非常仔细地检查每一个非常重要的细节，非常感谢你的帮助。"
        result_normal = self.compressor.compress(prompt, aggressive=False)
        result_aggressive = self.compressor.compress(prompt, aggressive=True)
        
        self.assertLessEqual(
            result_aggressive.compressed_tokens,
            result_normal.compressed_tokens
        )
    
    def test_list_compression(self):
        """测试列表压缩"""
        prompt = """任务列表：
任务1: 完成数据清洗
任务2: 完成数据清洗
任务3: 完成数据清洗
任务4: 完成数据清洗
任务5: 完成数据清洗"""
        
        result = self.compressor.compress(prompt)
        self.assertGreater(result.original_tokens, 0)
        self.assertIsNotNone(result.compressed)
        self.assertGreaterEqual(result.confidence, 0.5)


class TestTokenAnalyzer(unittest.TestCase):
    """测试Token分析器"""
    
    def setUp(self):
        self.analyzer = TokenAnalyzer()
    
    def test_estimate_tokens(self):
        """测试Token估算"""
        text = "这是一个测试文本，用于验证Token估算功能。"
        tokens = self.analyzer.estimate_tokens(text)
        
        expected = len(text) // 2
        self.assertAlmostEqual(tokens, expected, delta=5)
    
    def test_analyze_prompt(self):
        """测试提示词分析"""
        prompt = """非常非常重要的提示词：
请你非常仔细地完成以下任务：
- 第一点
- 第二点
- 第三点

非常感谢你的帮助！"""
        
        result = self.analyzer._analyze_prompt(prompt, "test.md")
        
        self.assertGreater(result.total_tokens, 0)
        self.assertGreater(len(result.suggestions), 0)


class TestLearner(unittest.TestCase):
    """测试学习器"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.learner = TokenOptimizationLearner(self.temp_dir)
    
    def test_learn_from_case(self):
        """测试从案例学习"""
        case_id = self.learner.learn_from_case(
            original="这是一个很长的原始代码",
            optimized="精简版",
            strategy="test_strategy",
            success_rating=0.9
        )
        
        self.assertIsNotNone(case_id)
        self.assertEqual(len(self.learner.cases), 1)
    
    def test_suggest_optimizations(self):
        """测试优化建议"""
        self.learner.learn_from_case(
            original="非常仔细地完成任务",
            optimized="仔细完成",
            strategy="remove_redundant",
            success_rating=0.95
        )
        
        suggestions = self.learner.suggest_optimizations("非常仔细地检查代码")
        self.assertIsInstance(suggestions, list)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestPromptCompressor))
    suite.addTests(loader.loadTestsFromTestCase(TestTokenAnalyzer))
    suite.addTests(loader.loadTestsFromTestCase(TestLearner))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

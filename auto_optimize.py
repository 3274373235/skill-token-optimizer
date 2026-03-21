#!/usr/bin/env python3
"""
自动优化器 - 一键优化技能/智能体/工作流的Token使用
"""

import sys
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# 导入其他模块
from analyzer import TokenAnalyzer
from compressor import PromptCompressor
from learner import TokenOptimizationLearner


class TokenAutoOptimizer:
    """Token自动优化器"""
    
    def __init__(self, target_path: str, backup: bool = True):
        self.target_path = Path(target_path)
        self.backup = backup
        self.analyzer = TokenAnalyzer()
        self.compressor = PromptCompressor()
        self.learner = TokenOptimizationLearner()
        
        self.optimization_log = []
        self.total_saved = 0
        
    def optimize_skill(self, auto_fix: bool = False) -> Dict:
        """
        优化整个技能
        
        Args:
            auto_fix: 是否自动应用修复
        
        Returns:
            优化报告
        """
        print(f"🔍 开始分析: {self.target_path}")
        
        # 1. 备份
        if self.backup and auto_fix:
            self._create_backup()
        
        # 2. 分析所有文件
        analysis_results = self.analyzer.analyze_directory(str(self.target_path))
        
        if not analysis_results:
            return {"status": "error", "message": "未找到可优化文件"}
        
        # 3. 生成优化方案
        optimizations = []
        
        for result in analysis_results:
            file_opts = self._optimize_file(result, auto_fix)
            optimizations.extend(file_opts)
        
        # 4. 生成报告
        report = self._generate_report(analysis_results, optimizations)
        
        # 5. 记录学习
        if auto_fix:
            self._record_learning(optimizations)
        
        return report
    
    def _create_backup(self):
        """创建备份"""
        backup_dir = Path(f"{self.target_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        if self.target_path.is_dir():
            shutil.copytree(self.target_path, backup_dir)
        else:
            shutil.copy2(self.target_path, backup_dir)
        print(f"📦 已创建备份: {backup_dir}")
    
    def _optimize_file(self, analysis_result, auto_fix: bool) -> List[Dict]:
        """优化单个文件"""
        file_path = Path(analysis_result.file_path)
        
        if not file_path.exists():
            return optimizations
        
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        
        # 根据文件类型选择优化策略
        if file_path.suffix == '.md':
            # 优化提示词
            compressed = self.compressor.compress(content, aggressive=False)
            
            if compressed.compressed_tokens < compressed.original_tokens * 0.9:
                opt = {
                    "file": str(file_path),
                    "type": "prompt_compression",
                    "strategy": "semantic_compression",
                    "original_tokens": compressed.original_tokens,
                    "optimized_tokens": compressed.compressed_tokens,
                    "saved": compressed.original_tokens - compressed.compressed_tokens,
                    "confidence": compressed.confidence,
                    "strategies_used": compressed.strategy_used
                }
                optimizations.append(opt)
                
                if auto_fix and compressed.confidence > 0.75:
                    file_path.write_text(compressed.compressed, encoding='utf-8')
                    opt["applied"] = True
                    self.total_saved += opt["saved"]
        
        elif file_path.suffix in ['.py', '.js', '.ts']:
            # 优化代码
            for suggestion in analysis_result.suggestions:
                if suggestion.get("type") == "重复代码":
                    # 应用代码优化
                    optimized = self._apply_code_optimization(content, suggestion)
                    
                    if optimized != content:
                        opt = {
                            "type": "code_optimization",
                            "strategy": suggestion["type"],
                            "description": suggestion["suggestion"],
                            "potential_saving": suggestion.get("potential_saving", 0)
                        }
                        
                            file_path.write_text(optimized, encoding='utf-8')
                            content = optimized
                            self.total_saved += opt["potential_saving"]
                
                elif suggestion.get("type") == "导入过多":
                    # 优化导入
                    optimized = self._optimize_imports(content)
                    
                        opt = {
                            "type": "import_optimization",
                            "strategy": "remove_unused",
                        }
                        
        
        # 应用学习到的模式
        learned_opts = self._apply_learned_patterns(file_path, content, auto_fix)
        optimizations.extend(learned_opts)
        
    
    def _apply_code_optimization(self, content: str, suggestion: Dict) -> str:
        """应用代码优化"""
        # 简化版：合并重复行
        lines = content.split('\n')
        seen = {}
        new_lines = []
        
        for line in lines:
            stripped = line.strip()
            if stripped in seen and len(stripped) > 10:
                # 替换为函数调用或变量引用
                continue
            seen[stripped] = True
            new_lines.append(line)
        
        return '\n'.join(new_lines)
    
    def _optimize_imports(self, content: str) -> str:
        """优化导入语句"""
        imports = []
        other_lines = []
        
            if line.strip().startswith(('import ', 'from ')):
                imports.append(line)
            else:
                other_lines.append(line)
        
        # 检查哪些导入被使用了
        other_content = '\n'.join(other_lines)
        used_imports = []
        
        for imp in imports:
            module = imp.split()[1].split('.')[0] if len(imp.split()) > 1 else ""
            if module and module in other_content:
                used_imports.append(imp)
        
        return '\n'.join(used_imports + [''] + other_lines)
    
    def _apply_learned_patterns(self, file_path: Path, content: str, auto_fix: bool) -> List[Dict]:
        """应用学习到的优化模式"""
        
        suggestions = self.learner.suggest_optimizations(content, str(file_path))
        
        for suggestion in suggestions:
            if suggestion["confidence"] > 0.7:
                opt = {
                    "type": "learned_pattern",
                    "strategy": suggestion["strategy"],
                    "pattern_key": suggestion["pattern_key"],
                    "confidence": suggestion["confidence"],
                    "frequency": suggestion["frequency"]
                }
                
                if auto_fix and suggestion["confidence"] > 0.85:
                    # 应用学习到的优化
                    # 这里简化处理，实际应该更精确地替换
        
    
    def _generate_report(self, analysis_results, optimizations) -> Dict:
        """生成优化报告"""
        total_original = sum(r.total_tokens for r in analysis_results)
        total_saved = sum(o.get("saved", o.get("potential_saving", 0)) for o in optimizations)
        
        applied_count = sum(1 for o in optimizations if o.get("applied"))
        
        # 按类型分组
        by_type = {}
        for opt in optimizations:
            t = opt.get("type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "target": str(self.target_path),
            "summary": {
                "files_analyzed": len(analysis_results),
                "total_original_tokens": total_original,
                "optimizations_found": len(optimizations),
                "optimizations_applied": applied_count,
                "estimated_tokens_saved": total_saved,
                "saving_percentage": round(total_saved / total_original * 100, 2) if total_original > 0 else 0
            },
            "by_type": by_type,
            "top_optimizations": sorted(
                optimizations,
                key=lambda x: x.get("saved", x.get("potential_saving", 0)),
                reverse=True
            )[:10],
            "all_optimizations": optimizations
        }
    
    def _record_learning(self, optimizations: List[Dict]):
        """记录学习"""
            if opt.get("applied"):
                self.learner.learn_from_case(
                    original="",  # 简化版，实际应保存原始内容
                    optimized="",
                    strategy=opt.get("strategy", "unknown"),
                    context=opt.get("file", ""),
                    success_rating=0.9 if opt.get("confidence", 0) > 0.8 else 0.7
                )
    
    def optimize_workflow(self, workflow_file: str, auto_fix: bool = False) -> Dict:
        """优化工作流"""
        workflow_path = Path(workflow_file)
        
        if not workflow_path.exists():
            return {"status": "error", "message": "工作流文件不存在"}
        
        workflow = json.loads(workflow_path.read_text())
        
        # 分析工作流结构
        
        # 1. 检查是否可以并行化
        if self._can_parallelize(workflow):
            optimizations.append({
                "type": "workflow_parallelization",
                "description": "串行步骤可改为并行执行",
                "potential_saving": "30-50%"
            })
        
        # 2. 检查重复步骤
        duplicates = self._find_duplicate_steps(workflow)
        if duplicates:
                "type": "workflow_deduplication",
                "description": f"发现 {len(duplicates)} 个重复步骤",
                "potential_saving": "20-40%"
            })
        
        # 3. 检查提示词长度
        for step in workflow.get("steps", []):
            if "prompt" in step:
                prompt = step["prompt"]
                compressed = self.compressor.compress(prompt, aggressive=False)
                
                if compressed.compressed_tokens < compressed.original_tokens * 0.8:
                        "type": "workflow_prompt_compression",
                        "step": step.get("name", "unknown"),
                        "compressed_tokens": compressed.compressed_tokens,
                        "saved": compressed.original_tokens - compressed.compressed_tokens
                    })
                    
                        step["prompt"] = compressed.compressed
        
            workflow_path.write_text(json.dumps(workflow, indent=2, ensure_ascii=False))
        
        return {
            "workflow_file": workflow_file,
            "optimizations": optimizations
        }
    
    def _can_parallelize(self, workflow: Dict) -> bool:
        """检查是否可以并行化"""
        steps = workflow.get("steps", [])
        # 简化判断：如果有超过3个独立步骤
        return len(steps) >= 3
    
    def _find_duplicate_steps(self, workflow: Dict) -> List[Dict]:
        """查找重复步骤"""
        seen = {}
        duplicates = []
        
        for i, step in enumerate(steps):
            step_str = json.dumps(step, sort_keys=True)
            if step_str in seen:
                duplicates.append({
                    "step_index": i,
                    "duplicate_of": seen[step_str]
                })
            else:
                seen[step_str] = i
        
        return duplicates


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Token自动优化器 - 优化技能/智能体/工作流的Token使用'
    )
    parser.add_argument('target', help='要优化的目标路径')
    parser.add_argument('--auto-fix', action='store_true', help='自动应用修复')
    parser.add_argument('--no-backup', action='store_true', help='不创建备份')
    parser.add_argument('--workflow', help='优化工作流文件')
    parser.add_argument('-o', '--output', help='输出报告文件')
    
    args = parser.parse_args()
    
    optimizer = TokenAutoOptimizer(
        args.target,
        backup=not args.no_backup
    )
    
    if args.workflow:
        report = optimizer.optimize_workflow(args.workflow, args.auto_fix)
    else:
        report = optimizer.optimize_skill(args.auto_fix)
    
    # 输出报告
    print("\n" + "="*60)
    print("📊 Token自动优化报告")
    print("="*60)
    
    if report["status"] == "success":
        summary = report["summary"]
        print(f"\n✅ 分析完成!")
        print(f"   文件数: {summary['files_analyzed']}")
        print(f"   原始Token: {summary['total_original_tokens']:,}")
        print(f"   发现优化点: {summary['optimizations_found']}")
        print(f"   已应用: {summary['optimizations_applied']}")
        print(f"   预计节省: {summary['estimated_tokens_saved']:,} ({summary['saving_percentage']}%)")
        
        if report.get("top_optimizations"):
            print(f"\n🔧 主要优化项:")
            for i, opt in enumerate(report["top_optimizations"][:5], 1):
                saved = opt.get("saved", opt.get("potential_saving", 0))
                print(f"   {i}. [{opt['type']}] {opt.get('strategy', '')} - 节省 {saved} tokens")
        
        if args.auto_fix:
            print(f"\n✨ 已自动应用优化!")
        else:
            print(f"\n💡 使用 --auto-fix 自动应用优化")
    else:
        print(f"\n❌ 优化失败: {report.get('message', '未知错误')}")
    
    # 保存报告
    if args.output:
        Path(args.output).write_text(
            json.dumps(report, indent=2, ensure_ascii=False)
        )
        print(f"\n📁 报告已保存: {args.output}")


if __name__ == "__main__":
    main()

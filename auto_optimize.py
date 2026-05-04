#!/usr/bin/env python3
"""
自动优化器 v1.2 - 一键优化技能/智能体/工作流的Token使用
支持预算感知路由
"""

import sys
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from analyzer import TokenAnalyzer
from compressor import PromptCompressor
from learner import TokenOptimizationLearner
from monitor import TokenMonitor


class TokenAutoOptimizer:
    """Token自动优化器 v1.2"""

    def __init__(self, target_path: str, backup: bool = True):
        self.target_path = Path(target_path)
        self.backup = backup
        self.analyzer = TokenAnalyzer()
        self.compressor = PromptCompressor()
        self.learner = TokenOptimizationLearner()
        self.monitor = TokenMonitor()
        self.optimization_log = []
        self.total_saved = 0

    def optimize_skill(self, auto_fix: bool = False, budget_aware: bool = True) -> Dict:
        print(f"🔍 开始分析: {self.target_path}")
        if self.backup and auto_fix:
            self._create_backup()

        analysis_results = self.analyzer.analyze_directory(str(self.target_path))
        if not analysis_results:
            return {"status": "error", "message": "未找到可优化文件"}

        # 获取剩余预算比例
        remaining_budget_ratio = 1.0
        if budget_aware:
            stats = self.monitor.get_stats("day")
            used = stats["budget"]["used_today"]
            daily_budget = stats["budget"]["daily"]
            remaining_budget_ratio = max(0, (daily_budget - used) / daily_budget) if daily_budget > 0 else 1.0

        optimizations = []
        for result in analysis_results:
            file_opts = self._optimize_file(result, auto_fix, remaining_budget_ratio)
            optimizations.extend(file_opts)

        report = self._generate_report(analysis_results, optimizations)
        if auto_fix:
            self._record_learning(optimizations)
            # 记录本次优化消耗的Token估算
            self.monitor.record_usage("auto_optimize", report["summary"]["estimated_tokens_saved"], "optimization")
        return report

    def _create_backup(self):
        backup_dir = Path(f"{self.target_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        if self.target_path.is_dir():
            shutil.copytree(self.target_path, backup_dir)
        else:
            shutil.copy2(self.target_path, backup_dir)
        print(f"📦 已创建备份: {backup_dir}")

    def _optimize_file(self, analysis_result, auto_fix: bool, budget_ratio: float) -> List[Dict]:
        file_path = Path(analysis_result.file_path)
        if not file_path.exists():
            return []
        content = file_path.read_text(encoding='utf-8')
        optimizations = []
        # 根据文件类型选择优化策略
        if file_path.suffix == '.md':
            # 预算感知压缩
            compressed = self.compressor.smart_compress(content, budget_remaining=budget_ratio)
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
                if auto_fix and compressed.confidence > 0.7:
                    file_path.write_text(compressed.compressed, encoding='utf-8')
                    opt["applied"] = True
                    self.total_saved += opt["saved"]
        elif file_path.suffix in ['.py', '.js', '.ts']:
            for suggestion in analysis_result.suggestions:
                if suggestion.get("type") == "重复代码":
                    optimized = self._apply_code_optimization(content, suggestion)
                    if optimized != content:
                        opt = {
                            "type": "code_optimization",
                            "strategy": suggestion["type"],
                            "description": suggestion["suggestion"],
                            "potential_saving": suggestion.get("saving", 10),
                            "file": str(file_path)
                        }
                        if auto_fix:
                            file_path.write_text(optimized, encoding='utf-8')
                            content = optimized
                            opt["applied"] = True
                            self.total_saved += opt["potential_saving"]
                        optimizations.append(opt)
                elif suggestion.get("type") == "导入过多":
                    optimized = self._optimize_imports(content)
                    if optimized != content:
                        opt = {
                            "type": "import_optimization",
                            "strategy": "remove_unused",
                            "file": str(file_path)
                        }
                        if auto_fix:
                            file_path.write_text(optimized, encoding='utf-8')
                            content = optimized
                            opt["applied"] = True
                        optimizations.append(opt)
        # 应用学习到的模式
        learned_opts = self._apply_learned_patterns(file_path, content, auto_fix)
        optimizations.extend(learned_opts)
        return optimizations

    def _apply_code_optimization(self, content: str, suggestion: Dict) -> str:
        """应用代码优化：合并重复行（简单示例）"""
        lines = content.split('\n')
        seen = {}
        new_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped in seen and len(stripped) > 10:
                continue
            seen[stripped] = True
            new_lines.append(line)
        return '\n'.join(new_lines)

    def _optimize_imports(self, content: str) -> str:
        """优化导入语句：移除未使用的导入"""
        lines = content.split('\n')
        imports = []
        other_lines = []
        for line in lines:
            if line.strip().startswith(('import ', 'from ')):
                imports.append(line)
            else:
                other_lines.append(line)
        other_content = '\n'.join(other_lines)
        used_imports = []
        for imp in imports:
            module = imp.split()[1].split('.')[0] if len(imp.split()) > 1 else ""
            if module and module in other_content:
                used_imports.append(imp)
        return '\n'.join(used_imports + [''] + other_lines)

    def _apply_learned_patterns(self, file_path: Path, content: str, auto_fix: bool) -> List[Dict]:
        """应用学习到的文本优化模式"""
        suggestions = self.learner.suggest_optimizations(content, str(file_path))
        optimizations = []
        for sugg in suggestions:
            if sugg.get("confidence", 0) > 0.7:
                opt = {
                    "type": "learned_pattern",
                    "strategy": sugg["strategy"],
                    "pattern_key": sugg.get("pattern_key", ""),
                    "confidence": sugg["confidence"],
                    "frequency": sugg.get("frequency", 1),
                    "file": str(file_path)
                }
                if auto_fix and sugg["confidence"] > 0.85 and sugg.get("pattern_key"):
                    # 应用替换模式
                    pattern = sugg["pattern_key"]
                    replacement = sugg.get("replacement", "")
                    new_content = re.sub(pattern, replacement, content)
                    if new_content != content:
                        file_path.write_text(new_content, encoding='utf-8')
                        opt["applied"] = True
                        self.total_saved += sugg.get("example_saving", 5)
                optimizations.append(opt)
        return optimizations

    def _generate_report(self, analysis_results, optimizations) -> Dict:
        total_original = sum(r.total_tokens for r in analysis_results)
        total_saved = sum(o.get("saved", o.get("potential_saving", 0)) for o in optimizations if o.get("applied", False))
        applied_count = sum(1 for o in optimizations if o.get("applied"))
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
                [o for o in optimizations if o.get("saved", o.get("potential_saving", 0)) > 0],
                key=lambda x: x.get("saved", x.get("potential_saving", 0)),
                reverse=True
            )[:10],
            "all_optimizations": optimizations
        }

    def _record_learning(self, optimizations: List[Dict]):
        for opt in optimizations:
            if opt.get("applied"):
                self.learner.learn_from_case(
                    original="",  # 简化版，实际可存原文内容（避免过大数据）
                    optimized="",
                    strategy=opt.get("strategy", "unknown"),
                    context=opt.get("file", ""),
                    success_rating=0.9 if opt.get("confidence", 0) > 0.8 else 0.7
                )

    def optimize_workflow(self, workflow_file: str, auto_fix: bool = False) -> Dict:
        workflow_path = Path(workflow_file)
        if not workflow_path.exists():
            return {"status": "error", "message": "工作流文件不存在"}
        workflow = json.loads(workflow_path.read_text())
        optimizations = []
        # 1. 并行化检查
        if self._can_parallelize(workflow):
            optimizations.append({
                "type": "workflow_parallelization",
                "description": "串行步骤可改为并行执行",
                "potential_saving": "30-50%"
            })
        # 2. 重复步骤检查
        duplicates = self._find_duplicate_steps(workflow)
        if duplicates:
            optimizations.append({
                "type": "workflow_deduplication",
                "description": f"发现 {len(duplicates)} 个重复步骤",
                "potential_saving": "20-40%"
            })
        # 3. 压缩提示词
        steps = workflow.get("steps", [])
        for step in steps:
            if "prompt" in step:
                prompt = step["prompt"]
                compressed = self.compressor.compress(prompt, aggressive=False)
                if compressed.compressed_tokens < compressed.original_tokens * 0.8:
                    optimizations.append({
                        "type": "workflow_prompt_compression",
                        "step": step.get("name", "unknown"),
                        "saved": compressed.original_tokens - compressed.compressed_tokens
                    })
                    if auto_fix:
                        step["prompt"] = compressed.compressed
        if auto_fix:
            workflow_path.write_text(json.dumps(workflow, indent=2, ensure_ascii=False))
        return {"workflow_file": workflow_file, "optimizations": optimizations}

    def _can_parallelize(self, workflow: Dict) -> bool:
        steps = workflow.get("steps", [])
        return len(steps) >= 3

    def _find_duplicate_steps(self, workflow: Dict) -> List[Dict]:
        steps = workflow.get("steps", [])
        seen = {}
        duplicates = []
        for i, step in enumerate(steps):
            step_str = json.dumps(step, sort_keys=True)
            if step_str in seen:
                duplicates.append({"step_index": i, "duplicate_of": seen[step_str]})
            else:
                seen[step_str] = i
        return duplicates


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Token自动优化器 v1.2')
    parser.add_argument('target', help='要优化的目标路径')
    parser.add_argument('--auto-fix', action='store_true', help='自动应用修复')
    parser.add_argument('--no-backup', action='store_true', help='不创建备份')
    parser.add_argument('--workflow', help='优化工作流文件')
    parser.add_argument('--no-budget-aware', action='store_true', help='禁用预算感知路由')
    parser.add_argument('-o', '--output', help='输出报告文件')
    args = parser.parse_args()

    optimizer = TokenAutoOptimizer(args.target, backup=not args.no_backup)
    if args.workflow:
        report = optimizer.optimize_workflow(args.workflow, args.auto_fix)
    else:
        report = optimizer.optimize_skill(args.auto_fix, budget_aware=not args.no_budget_aware)

    print("\n" + "="*60)
    print("📊 Token自动优化报告 v1.2")
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
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2, ensure_ascii=False))
        print(f"\n📁 报告已保存: {args.output}")

if __name__ == "__main__":
    main()

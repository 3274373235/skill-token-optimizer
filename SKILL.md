# Token经济优化器

**名称**: `token-economy-optimizer` | **版本**: 1.0.0 | **类型**: Meta-Skill

## 🎯 简介

优化AI技能、提示词、工作流的Token使用量，具有自学习能力。

## 🚀 快速开始

```bash
# 分析文件
python3 analyzer.py skill.md

# 优化技能
python3 optimize.py ./skill/ --auto-fix

# 压缩提示词
python3 compressor.py "长提示词..."

# 监控使用
python3 monitor.py --watch ./project/
```

## 📊 优化效果

| 类型 | 节省比例 |
|------|----------|
| 提示词压缩 | 30-60% |
| 代码优化 | 15-40% |
| 工作流优化 | 20-50% |

## 🔧 组件

- **analyzer.py** - Token分析器
- **optimizer.py** - 优化引擎  
- **compressor.py** - 提示词压缩
- **learner.py** - 学习器
- **monitor.py** - 监控器

## 💡 使用示例

```python
from compressor import PromptCompressor

comp = PromptCompressor()
result = comp.compress("请你非常仔细地完成...")
print(f"节省: {result.original_tokens - result.compressed_tokens} tokens")
```

## 📝 配置文件

创建 `.token_opt_config.json`:
```json
{
  "daily_budget": 10000,
  "compression_level": "balanced"
}
```

## 🔗 依赖

- Python 3.8+
- 无第三方依赖

## 📄 License

MIT

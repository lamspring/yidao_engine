# 归档说明

以下文件已被统一工作流 `main.py` + `pipeline/` 取代，归档后可从根目录移除以保持整洁。

## 阶段测试脚本（功能已并入 pipeline/）

| 文件 | 对应 pipeline 模块 |
|------|-------------------|
| `stage1_baseline.py` | `pipeline/world_runner.py` + `pipeline/semantic.py` |
| `stage2_llm_test.py` | `pipeline/llm_client.py` + `pipeline/prompts.py` |
| `stage2_v2_llm_test.py` | 同上 |
| `stage2_v3_llm_test.py` | 同上 |
| `stage2_v4_tension_test.py` | 同上 |
| `stage4_continuous_narrative.py` | `main.py --mode single` |
| `stage5_multi_entity.py` | `main.py --mode dual` |
| `stage6_family_epic.py` | `main.py --mode family` |
| `stage6_v2_polished.py` | `main.py --mode family --style polished` |

## 阶段输出文件（运行时生成，可清理）

- `stage1_*.json`（6 个）
- `stage2_*.txt` + `stage2_*.json`（~20 个）
- `stage4_*.txt`（5 个）
- `stage5_*.txt`（4 个）
- `stage6_*.txt`（4 个）

## 残留测试输出

- `test_output.txt`
- `test_err.txt`
- `test_out.txt`
- `test_observer.txt`

## 如何归档

```bash
mkdir archive
mv stage*.py stage*.txt stage*.json archive/
mv test_output.txt test_err.txt test_out.txt test_observer.txt archive/
```

## 保留的测试

- `test_p3.py` — 体用两轮流水线独立测试
- `test_p4.py` — 事件引擎独立测试
- `verify_changes.py` — 改动验证脚本

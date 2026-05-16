# 易道引擎变更记录

## v5.2 — 2026-05-15

### 核心引擎改动

#### 64 息卦运周期势能调制 (`kernel.py`)
- **旧**：`senescence = 0.025 * (stable_age > 80)` — flat rate，80 息后恒定加速
- **新**：正弦波调制 `cycle_boost = 0.03 * 0.5*(1-cos(2π·age%64/64))`
  - 0→32 息：势能加速积累（旺相期）
  - 32→48 息：势能达到峰值（临界期）
  - 48→64 息：若未爆发则回落（休养期），残余势能叠加至下一周期
  - 卦变发生时 `pot=0, stable_age=0`，周期重置
- **哲学**：活跃结构（气象强）基础积累慢，可跨越多个周期；死寂结构（气象弱）首周期即爆——"反者道之动：表面最稳者，内在最危"

#### 向量化 hugua 和 yao_bian (`kernel.py`)
- 新增 `hugua(S)` 和 `yao_bian(S, positions)` 向量化版本（NumPy 位运算）
- `_resolve_transformations` 中 flip 处理从逐点 Python 循环改为按 phase 三分组批量操作
- 保留了 `hugua_scalar` 和 `yao_bian_scalar` 向后兼容

#### 索引体系统一 (`observer.py`)
- 新增 `_TRIGRAM_VALUES` 和 `_TRIGRAM_INDEX` 双向映射
- `get_dominant_trigram()` 现在返回卦值 (0,9,18,27,36,45,54,63) 而非 0-7 索引
- `get_relation_term()` 接受卦值（向后兼容 0-7 索引）
- `body_nature.py` 和 `observer.py` 统一用卦值体系

### 配置与测试清理

- **API_BASE 环境变量化**：全部 9 个 stage 测试脚本的 `API_BASE` 改为从 `YIDAO_API_BASE` 环境变量读取（含默认 fallback）
- **typo 修复**：`stage6_v2_polished.py` 中 `xiaomimimimo.com` 修正为 `xiaomimimo.com`
- **`.env.example`**：新增 `YIDAO_API_BASE` 配置项

### 验证器收紧 (`pipeline/validator.py`)
- `validate_raw`：7 项叙事质量检查从单关键词命中改为多关键词阈值（≥2）
- `validate_polished`：动作描写从 `any()`→`≥3` 种独特动词

### 文档更新
- `README.md`：势能积累公式和反向势能描述更新为 64 息卦运周期
- `AGENTS.md`：演算规则行更新
- `QUICKSTART.md`：环境变量表新增 `YIDAO_API_BASE`

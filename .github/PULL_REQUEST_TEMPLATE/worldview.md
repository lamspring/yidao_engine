## 世界观配置提交

### 基本信息

- **世界观名称**：
- **文件名**：`configs/worldviews/{名称}.json`
- **灵感来源**（电影/小说/游戏/历史/原创）：

### 覆盖协议

- [ ] `承载`（坤）
- [ ] `激变`（震）
- [ ] `深渊`（坎）
- [ ] `渗透`（巽）
- [ ] `止界`（艮）
- [ ] `显文明`（离）
- [ ] `交换`（兑）
- [ ] `创序`（乾）

> 未覆盖的协议请在此说明原因：

### 语库变体

- [ ] 无 `lexicon_variants`
- [ ] 有 `lexicon_variants`，手动编写
- [ ] 有 `lexicon_variants`，使用 `tools/generate_worldview_lexicon.py` 生成

如有变体，生成参数：
```bash
python tools/generate_worldview_lexicon.py --worldview XXX --provider XXX --variants N
```

### 自检清单

- [ ] JSON 格式通过 `python -m json.tool` 验证
- [ ] `python main.py --no-llm --worldview XXX --ticks 100` 运行正常
- [ ] 所有必填字段已填写
- [ ] `lexicon_variants`（如有）符合质量标准（40-80 字、纯感官、无系统术语）
- [ ] 已阅读 `CONTRIBUTING.md`

### 示例输出（可选）

粘贴一段你最喜欢的 `lexicon_variants`：

```
（粘贴此处）
```

### 备注

（任何需要维护者特别说明的内容）

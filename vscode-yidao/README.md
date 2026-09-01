# 易道引擎 VS Code 插件

在 VS Code 中通过图形界面交互式推演易道世界。

## 功能

- 🎬 **可视化控制**：推进世界、生成叙事、调整摄像机，全部通过按钮操作
- 📊 **实时状态**：显示当前 tick、各实体卦象/势能/相位、摄像机配置
- 📝 **叙事渲染**：LLM 生成的叙事直接显示在面板中，支持 Markdown
- 🔄 **重新生成**：对叙事不满意？一键 reroll，不改变世界状态
- 💾 **会话管理**：保存/加载完整会话，跨天继续推演

## 安装

### 方法一：从源码安装（开发）

```bash
# 1. 进入插件目录
cd vscode-yidao

# 2. 安装依赖
npm install

# 3. 编译
npm run compile

# 4. 在 VS Code 中打开此目录，按 F5 启动调试
```

### 方法二：打包为 .vsix（推荐）

```bash
cd vscode-yidao
npm install
npm run compile
# 需要安装 vsce: npm install -g @vscode/vsce
vsce package
# 会生成 vscode-yidao-0.1.0.vsix
code --install-extension vscode-yidao-0.1.0.vsix
```

## 配置

在 VS Code 设置中搜索 "易道引擎"：

| 设置项 | 说明 | 默认值 |
|--------|------|--------|
| `yidao.pythonPath` | Python 可执行文件路径 | `python` |
| `yidao.apiPort` | API 服务器端口 | `8765` |
| `yidao.mode` | 推演模式 | `family` |
| `yidao.provider` | LLM 提供商 | `deepseek` |
| `yidao.worldview` | 世界观配置名 | `null` |

**环境变量**：确保设置了对应提供商的 API Key：
```bash
export DEEPSEEK_API_KEY="sk-xxxx"
```

## 使用

1. **打开面板**：按 `Ctrl+Shift+P`，输入 "易道: 打开推演面板"
2. **启动服务器**：首次打开会自动启动 Python API 服务器
3. **推进世界**：在 "推进 ticks" 输入框填入数值，点击"推进"
4. **生成叙事**：点击"解释此幕"，等待 LLM 生成文本
5. **调整镜头**：在"聚焦"和"变体"下拉框选择，点击"设置"
6. **保存进度**：输入会话名称，点击"保存"

## 架构

```
VS Code 窗口
├── Webview Panel (UI: 按钮/表格/输出区)
│   ↑↓ postMessage
├── Extension Host (TypeScript)
│   ↑↓ HTTP fetch
└── Python API 服务器 (api_server.py)
    └── InteractiveRunner
```

## 快捷键

| 命令 | 快捷键 |
|------|--------|
| 打开推演面板 | `Ctrl+Shift+P` → "易道: 打开推演面板" |
| 启动服务器 | `Ctrl+Shift+P` → "易道: 启动推演服务器" |
| 停止服务器 | `Ctrl+Shift+P` → "易道: 停止推演服务器" |

## 故障排除

**服务器启动超时**
- 检查 `yidao.pythonPath` 设置是否正确
- 检查是否已安装 `numpy`
- 查看 VS Code 输出面板 → "易道引擎" 通道

**API 连接失败**
- 检查端口是否被占用（默认 8765）
- 检查防火墙是否阻止 localhost 通信

**LLM 调用失败**
- 检查对应提供商的 API Key 环境变量是否设置
- 检查网络连接

## 许可证

代码 Apache-2.0 / 文档 CC BY-SA 4.0

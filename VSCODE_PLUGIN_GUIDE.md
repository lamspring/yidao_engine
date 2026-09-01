# 易道推演 VS Code 插件使用手册

## 一、环境准备

### 1.1 必要依赖

| 依赖 | 版本要求 | 说明 |
|------|---------|------|
| Python | 3.10+ | 引擎核心运行环境 |
| Node.js | 18+ | VS Code 扩展编译 |
| VS Code | 1.85+ | 宿主编辑器 |
| numpy | 任意 | Python 数值计算 |

### 1.2 安装 Python 依赖

```bash
cd /c/Users/25476/yidao_engine
pip install numpy
```

### 1.3 配置 LLM 提供商

编辑 `configs/llm_providers.json`，确认你要使用的 provider 已列出：

```json
{
  "deepseek": {
    "base_url": "https://api.deepseek.com/v1",
    "api_key_env": "DEEPSEEK_API_KEY",
    "default_model": "deepseek-chat"
  }
}
```

**方式一：环境变量（推荐）**

```bash
# Windows CMD
set DEEPSEEK_API_KEY=sk-your-key-here

# Windows PowerShell
$env:DEEPSEEK_API_KEY="sk-your-key-here"

# Git Bash
export DEEPSEEK_API_KEY=sk-your-key-here
```

**方式二：插件面板内输入**

直接在「推演配置」面板的 API Key 框填入，会覆盖环境变量。

---

## 二、启动插件

### 2.1 打开工程

用 VS Code 打开 `vscode-yidao/` 文件夹作为工作区根目录：

```bash
code /c/Users/25476/yidao_engine/vscode-yidao
```

### 2.2 编译

按 `Ctrl+Shift+B` 执行默认构建任务，或终端运行：

```bash
npm run compile
```

### 2.3 启动调试（Extension Development Host）

按 `F5`，会弹出一个新的 VS Code 窗口（扩展开发宿主）。

### 2.4 启动推演服务器

在新窗口中按 `Ctrl+Shift+P`，输入并选择：

```
易道: 启动推演服务器
```

等待状态栏提示「推演服务器已启动」。

### 2.5 打开推演面板

再次按 `Ctrl+Shift+P`，选择：

```
易道: 打开推演面板
```

---

## 三、配置面板

面板顶部是「⚙️ 推演配置」区域，可折叠。首次使用建议先配置。

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| **大模型** | 选择 LLM 提供商 | `deepseek` |
| **API Key** | 你的 API 密钥；留空则读取环境变量 | 空 |
| **世界观** | 叙事世界观模板 | `默认` |
| **推演模式** | 实体数量与关系结构 | `family` |
| **文风** | 叙事润色程度 | `polished` |

### 3.1 世界观说明

- **默认**：无特殊世界观，纯六爻推演
- **修仙**：东方玄幻修真体系（`configs/worldviews/xiuxian.json`）
- **克苏鲁**：洛夫克拉夫特式恐怖（`configs/worldviews/cthulhu.json`）

### 3.2 推演模式说明

| 模式 | 实体数 | 关系结构 |
|------|--------|---------|
| `single` | 1 | 单人自观 |
| `dual` | 2 | 双人互动 |
| `family` | 6 | 父子母女六爻家庭 |

### 3.3 文风说明

- `polished`：润色后的文学叙事，带对话、感官描写、动作细节
- `raw`：原始输出，接近提示词直出

### 3.4 应用配置

修改配置后，点击 **「应用配置并重新初始化」**。这会：
1. 销毁当前世界状态
2. 用新配置重新初始化 `InteractiveRunner`
3. 清空叙事历史

---

## 四、主面板功能

### 4.1 状态栏

面板顶部显示当前世界快照：

| 字段 | 说明 |
|------|------|
| **Tick** | 当前时间步 |
| **聚焦** | 摄像机焦点（如 `family`、`father`） |
| **变体** | 当前锁定的变体语库（如 `dao`、`scifi`） |
| **幕数** | 已生成的叙事段落数 |
| **Tokens** | 累计消耗的 LLM token 数 |

### 4.2 实体状态

六爻家庭各成员的实时状态表：

| 列 | 说明 |
|----|------|
| 实体 | 成员 ID（如 `father`、`mother`） |
| 卦 | 当前卦象名 |
| 协议 | 身体协议标签 |
| 相位 | 当前相位（0–1） |
| 势能 | 当前势能值 |

### 4.3 控制按钮

| 按钮 | 功能 |
|------|------|
| **推进** | 按输入的 ticks 数推进世界（默认 150） |
| **解释此幕** | 捕获快照 → 构建语义包 → 调用 LLM → 生成叙事 |
| **重新生成** | 用上一次的相同输入重新调用 LLM（换种写法） |
| **重置世界** | 清空所有状态，回到 tick=0 |

### 4.4 聚焦与变体

| 控件 | 功能 |
|------|------|
| **聚焦** | 选择摄像机关注对象（`family` 或具体成员） |
| **变体锁定** | 强制使用某语库变体叙事（`dao`/`scifi`/`myth`/`exist`） |

### 4.5 保存与加载

输入会话名称，点击 **保存** / **加载**，状态文件保存在 `./states/` 目录。

---

## 五、典型推演流程

### 5.1 开始一局推演

1. 配置 provider 和 API Key
2. 选择世界观（可选）和模式
3. 点击 **应用配置并重新初始化**
4. 点击 **推进**（150 ticks）
5. 点击 **解释此幕** → 等待 LLM 生成叙事
6. 如不满意，点击 **重新生成**
7. 重复 4–6，推进下一幕

### 5.2 切换视角

在某幕推进后：
1. 在「聚焦」下拉框选择具体成员（如 `father`）
2. 点击 **设置**
3. 再点击 **解释此幕** → 叙事会以该成员视角展开

### 5.3 锁定变体

想让某幕用科幻风格：
1. 「变体锁定」选 `scifi`
2. 点击 **锁定**
3. 点击 **解释此幕**

---

## 六、日志与输出

### 6.1 操作日志

面板中部的灰色框记录所有操作结果、错误提示。

### 6.2 叙事输出

面板底部的白色框显示 LLM 生成的 Markdown 叙事，支持标题、粗体、分割线等基础渲染。

### 6.3 后端日志

查看 `View → Output → 易道引擎`，可看到 Python 服务器的 stdout/stderr：
- API 请求记录
- LLM 调用耗时
- 验证器检查结果

---

## 七、常见问题

### Q1：「推演服务器启动超时」

**原因**：`api_server.py` 依赖 `pipeline` 模块，但工作目录不对。

**解决**：确保插件目录下没有 `api_server.py` 副本（已删除）。插件会自动回退到父目录（`yidao_engine/api_server.py`）启动。

### Q2：「LLM 配置加载失败」

**原因**：环境变量未设置，且 API Key 框留空。

**解决**：
- 在配置面板填入 API Key，或
- 在终端设置环境变量后重启 VS Code

### Q3：中文乱码

**原因**：Windows CMD/PowerShell 默认 GBK 编码。

**解决**：使用 Git Bash，或在系统设置中将区域格式设为 UTF-8。

### Q4：无法打开面板

**原因**：
- 未按 `F5` 进入 Extension Development Host
- 扩展编译失败

**解决**：
1. 确认 `npm run compile` 无错误
2. 确认 `.vscode/launch.json` 存在
3. 按 `F5` 启动，在新窗口中调用命令

### Q5：世界观加载失败

**原因**：`configs/worldviews/{name}.json` 不存在。

**解决**：确认 `configs/worldviews/` 目录下有对应 `.json` 文件，或在配置面板选择「默认」。

---

## 八、快捷键（可选配置）

在 `vscode-yidao/package.json` 的 `keybindings` 中可自定义，例如：

```json
{
  "command": "yidao.openPanel",
  "key": "ctrl+shift+y",
  "when": "editorTextFocus"
}
```

---

## 九、文件结构速查

```
yidao_engine/
├── api_server.py              # HTTP API 服务器
├── configs/
│   ├── llm_providers.json     # LLM 提供商配置
│   └── worldviews/            # 世界观模板
│       ├── xiuxian.json
│       └── cthulhu.json
├── pipeline/
│   ├── interactive_runner.py  # 交互式推演核心
│   ├── config.py              # PipelineConfig / LLMConfig
│   ├── variant_store.py       # 变体语库
│   └── validator.py           # 输出验证器
└── vscode-yidao/              # VS Code 插件
    ├── src/
    │   ├── extension.ts       # 扩展入口
    │   ├── YidaoPanel.ts      # Webview 面板
    │   └── apiClient.ts       # HTTP 客户端
    ├── media/
    │   ├── index.html         # 面板 HTML
    │   ├── main.js            # 前端逻辑
    │   └── style.css          # 样式
    └── package.json
```

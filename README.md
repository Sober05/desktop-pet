# 🐱 Desktop Pet — 桌面像素猫宠物

一个住在你桌面上的像素猫，基于 PyQt5 + DeepSeek API。会走动、会睡觉、会聊天、还能帮你分析文件。

## ✨ 功能

- **AI 对话** — 点击猫聊天，DeepSeek API 驱动
- **文件分析** — 拖拽文件到猫身上，自动分析并总结
- **桌面漂浮** — 透明无边框窗口，可拖拽，始终置顶
- **空闲休眠** — 5 分钟不操作自动睡觉，回来动鼠标就醒
- **心情系统** — 互动加分，冷淡减分，心情低落时主动求关注
- **主动搭话** — 根据时间和心情偶尔冒泡聊天
- **系统托盘** — 最小化到托盘，右键菜单快速操作
- **剪贴板监控** — 复制文字时提示
- **位置记忆** — 重启恢复原位
- **6 种动画** — 待机 / 走路 / 思考 / 开心 / 睡觉 / 眨眼

## 🚀 快速开始

### 安装

```bash
# 1. 克隆仓库
git clone https://github.com/Sober05/desktop-pet.git
cd desktop-pet

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 API Key (二选一)
# 方法 A: 环境变量 (推荐)
set DEEPSEEK_API_KEY=sk-your-key-here      # Windows
export DEEPSEEK_API_KEY=sk-your-key-here   # macOS / Linux

# 方法 B: 配置文件
cp config.example.json config.json
# 编辑 config.json，填入 api_key

# 4. 启动
python main.py
```

### 自定义快捷启动

编辑 `config.json` 添加 `quick_launch`：

```json
{
  "api_key": "",
  "model": "deepseek-chat",
  "quick_launch": [
    {"name": "VS Code", "path": "C:\\path\\to\\Code.exe"},
    {"name": "Obsidian", "path": "C:\\path\\to\\Obsidian.exe"}
  ]
}
```

## 🎮 操作

| 操作 | 效果 |
|------|------|
| 单击猫 | 打开聊天 |
| 拖拽移动 | 移动猫的位置 |
| 拖拽文件 | AI 分析文件 |
| 右键 | 菜单（聊天/快速启动/置顶/睡觉/退出） |
| 系统托盘双击 | 显示/隐藏 |

## 🏗️ 架构

```
desktop-pet/
├── main.py          # 入口：单实例锁、健康检查、崩溃守护
├── pet_window.py    # 核心 UI：动画、渲染、鼠标、拖放
├── pet_systems.py   # 后台系统：托盘、菜单、空闲检测、心情
├── chat_dialog.py   # 对话气泡：聊天 UI + 历史持久化
├── ai_client.py     # DeepSeek API 封装 (OpenAI 兼容)
├── config_mgr.py    # 统一配置管理
├── file_handler.py  # 文件类型识别 + AI 分析提示词
├── sprites.py       # 16x16 像素猫精灵数据
├── error_log.py     # 错误日志工具
├── config.example.json  # 配置模板
└── requirements.txt
```

## 📋 依赖

- Python 3.8+
- PyQt5
- openai (Python SDK)

## 📄 License

MIT — 详见 [LICENSE](LICENSE)

## 🔒 隐私

- API Key 优先从环境变量 `DEEPSEEK_API_KEY` 读取
- `config.json` 已在 `.gitignore` 中排除，不会被提交
- 聊天记录保存在本地 `chat-history.json` 中（已 gitignore）

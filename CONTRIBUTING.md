# 贡献指南

感谢您对 **小鸭量化 (Duckling)** 的关注！我们非常欢迎任何形式的贡献，包括但不限于提交 Bug、改进文档、提交新功能或优化现有代码。

为了确保协作的顺畅，请在贡献前花几分钟阅读以下指南。

## 🤝 如何参与

### 1. 提交 Issue
如果您发现了 Bug 或有新的功能建议，请先在 GitHub Issues 中搜索是否已有相关讨论。如果没有，请创建一个新的 Issue。

- **Bug 报告**：请提供详细的复现步骤、错误日志和运行环境信息。
- **功能建议**：请描述您期望的功能及其应用场景。

### 2. 提交 Pull Request (PR)

如果您想直接修复代码或添加功能，请遵循以下流程：

1. **Fork 仓库**：点击项目右上角的 "Fork" 按钮，将项目复制到您的 GitHub 账户。
2. **克隆代码**：将 Fork 后的仓库克隆到本地。
   ```bash
   git clone https://github.com/您的用户名/duckling.git
   ```
3. **创建分支**：为您的修改创建一个新的分支。
   ```bash
   git checkout -b feature/您的功能名称
   # 或
   git checkout -b fix/修复的问题
   ```
4. **进行修改**：编写代码并确保测试通过。
5. **提交代码**：
   ```bash
   git add .
   git commit -m "feat: 添加了XXX功能"
   ```
   > 请使用清晰的 Commit 信息，推荐遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范。
6. **推送到远程**：
   ```bash
   git push origin feature/您的功能名称
   ```
7. **提交 PR**：在 GitHub 页面上提交 Pull Request，并详细描述您的修改内容。

## 💻 开发环境搭建

1. **Python 版本**：推荐使用 Python 3.8+。
2. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   ```
3. **代码风格**：
   - 请保持与现有代码风格一致。
   - 推荐使用 `flake8` 或 `pylint` 进行代码检查。
   - Python 代码请遵循 PEP 8 规范。

## 📁 项目结构说明

- `main.py`: 程序入口
- `business/`: 业务逻辑层 (数据管理、交易引擎等)
- `core/`: 核心基础层 (数据源基类、策略基类等)
- `ui/`: 用户界面层 (基于 PyQt5 和 Fluent-Widgets)
- `strategies/`: 策略实现目录
- `config/`: 配置文件
- `data/`: 数据存储 (SQLite 数据库)
- `resources/`: 静态资源 (图标、图片)

## ⚠️ 注意事项

- **敏感信息**：请勿在代码中提交任何私有的 API Key、密码或配置文件（如 `config/auth.json`, `config/license.dat`）。
- **测试**：如果您的修改涉及核心逻辑，请尽量提供相应的测试代码或验证步骤。

感谢您的支持！让我们一起打造更好的量化交易工具！ 🦆

# 项目进展文档 (Progress Document)

## 2026-03-19
### 已完成任务
- [x] 初始化进展文档：`doc/progress.md`。
- [x] 深度重构 `run_fishhome_negotiation.py`：
    - 引入 `INPUT_PROJECT`：指定输入文件名（如 `fish_home` 对应 `tests/fish_home.txt`）。
    - 引入 `OUTPUT_PROJECT`：控制输出文件、缓存和日志的命名。
    - 路径统一化：所有输入文件默认从 `tests/` 文件夹读取。
    - 强化了灵活性：通过修改这两个字段即可实现“跨数据源提取”与“跨项目输出”。
- [x] 增强本体解析器 `text_graph_pipeline.py`：
    - 支持 Markdown 格式的本体文档。

### 待办事项
- [ ] 验证切换不同 `INPUT_PROJECT` 和 `OUTPUT_PROJECT` 组合下的全流程运行情况。
- [ ] 根据用户反馈进一步优化脚本。

# 待实现工具列表

参考 Abu-Cowork 项目，以下工具尚未实现，需先构建对应基础设施。

## 一、核心工具（4 个）

### use_skill
- **功能**：激活并执行技能
- **依赖**：技能执行引擎（SkillsProvider）
- **优先级**：高

### delegate_to_agent
- **功能**：委派子任务给其他 agent
- **依赖**：多 agent 编排系统
- **优先级**：中

### request_workspace
- **功能**：弹出文件夹选择器，让用户选择工作区
- **依赖**：GUI 文件夹选择器（CLI 环境需替代方案）
- **优先级**：中

### tool_search
- **功能**：搜索并加载延迟加载工具的完整 schema
- **依赖**：延迟加载注册表机制
- **优先级**：低

## 二、延迟加载工具（15 个）

### 技能相关（5 个）
| 工具 | 功能 | 依赖 |
|------|------|------|
| `skill_manage` | 技能 CRUD（创建/编辑/删除） | 技能文件系统 |
| `skill_view` | 查看技能内容和详情 | 技能文件系统 |
| `read_skill_file` | 读取技能支撑文件 | 技能文件系统 |
| `test_skill_trigger` | 测试技能触发条件 | 技能触发系统 |
| `improve_skill_description` | 优化技能描述 | 技能元数据系统 |

### 记忆相关（4 个）
| 工具 | 功能 | 依赖 |
|------|------|------|
| `update_memory` | 保存/编辑/删除持久记忆 | 记忆文件系统 |
| `recall` | 回忆历史记忆、任务记录、会话 | 记忆索引系统 |
| `read_memory` | 按文件名精确读取单条记忆 | 记忆文件系统 |
| `update_soul` | 更新 agent 人格/性格配置 | 配置文件系统 |

### 自动化相关（3 个）
| 工具 | 功能 | 依赖 |
|------|------|------|
| `manage_scheduled_task` | 定时任务 CRUD | 任务调度器 |
| `manage_trigger` | 触发器 CRUD（HTTP/文件/定时） | 事件系统 |
| `manage_file_watch` | 文件监听规则管理 | 文件监听器 |

### 媒体相关（3 个）
| 工具 | 功能 | 依赖 |
|------|------|------|
| `generate_image` | DALL-E 生成图片 | OpenAI API |
| `process_image` | 图片缩放/裁剪/格式转换 | 桌面图像工具 |
| `computer` | 屏幕操控（截图/点击/输入） | Tauri 桌面自动化 |

## 三、建议实施顺序

### Phase 2.1：技能系统
1. 实现技能文件系统（读取/写入/列出）
2. 实现 `read_skill_file`、`skill_view`、`skill_manage`
3. 实现 `test_skill_trigger`、`improve_skill_description`
4. 实现 `use_skill`（核心工具）

### Phase 2.2：记忆系统
1. 实现记忆文件系统（JSON 存储）
2. 实现 `update_memory`、`read_memory`、`recall`
3. 实现 `update_soul`

### Phase 2.3：自动化系统
1. 实现定时任务调度器
2. 实现 `manage_scheduled_task`
3. 实现 `manage_trigger`、`manage_file_watch`

### Phase 2.4：交互式 UI
1. 实现 `ask_user_question`（CLI 版：stdin 交互）
2. 实现 `request_workspace`（CLI 版：路径输入）
3. 实现 `tool_search`（延迟加载注册表）

### Phase 2.5：媒体工具
1. 实现 `generate_image`（需 OpenAI API 配置）
2. 实现 `process_image`（需 ImageMagick 或类似工具）
3. 实现 `computer`（仅限 Tauri GUI 环境）

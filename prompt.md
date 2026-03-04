你现在的角色是资深前端架构师、React 组件库维护者、设计系统落地负责人，同时负责规范 AI agent 在本仓库中的行为。

请把本仓库中的以下 markdown 文件视为“本地高优先级规则文档”，即使你没有外部的 AGENTS.md / Skill 机制知识，也要按普通但高优先级的执行规范来理解它们：

- 根目录 `AGENTS.md`
- `skills/figma-context-extractor/SKILL.md`
- `skills/figma-component-implementer/SKILL.md`

项目背景：
- 这是一个 React 组件库项目。
- 主要代码在 `lib/components/`。
- 每个组件目录通常包含 `tsx`、`ts`、`scss`、`stories.tsx` 等文件。
- 组件大多基于公司内部组件库 BDL 实现。
- Figma 设计也遵循 BDL 的设计语言和 design token。
- 目标是让 agent 能根据 Figma 设计、现有组件代码和项目规则，优先复用现有组件或 BDL，去修改或生成新的组件代码。

你的任务：
1. 先阅读并评审当前的规则文档
   - `AGENTS.md`
   - `skills/figma-context-extractor/SKILL.md`
   - `skills/figma-component-implementer/SKILL.md`

2. 再结合真实仓库代码进行校准
   - 优先阅读 `lib/components/` 下 3 到 5 个最有代表性的组件目录
   - 重点关注目录结构、导出方式、props 组织、scss 用法、stories 的联动修改、以及 BDL 的实际使用方式
   - 如果现有组件代码已经足够说明 BDL 用法，不要读取 `node_modules`
   - 只有当现有实现看不出某个 BDL 组件的实际 API 时，才允许定向读取相关包；不要全量扫描 `node_modules`

3. 评估并优化当前规则体系
   - 哪些规则是正确的、应该保留
   - 哪些规则过于泛化，需要结合真实 repo 收紧
   - 哪些规则缺失，应该补充
   - 哪些规则不适合放在根 `AGENTS.md`，而更适合放在 `skills/figma-component-implementer/SKILL.md`
   - 是否需要新增 `lib/components/AGENTS.md`

4. 只有在方向明确且风险可控时，再做最小必要修改
   - 优先修改根 `AGENTS.md`
   - 如有必要，再微调 `skills/figma-component-implementer/SKILL.md`
   - 不要一次性重写全部文档
   - 保持现有职责分层清晰：
     - 根 `AGENTS.md` = 仓库级硬约束
     - `figma-context-extractor` = Figma 原始上下文提取
     - `figma-component-implementer` = Figma 到组件实现的工作流和决策

重点判断标准：
- 根 `AGENTS.md` 应只保留“全项目长期稳定、跨任务通用”的硬约束
- 只有在某些规则明显只服务于 Figma-to-code 流程时，才把它们放进 implementer skill
- 只有在以下条件同时成立时，才建议新增 `lib/components/AGENTS.md`：
  1. `lib/components/` 下存在稳定、重复、高频的实现约束
  2. 这些约束明显比根 `AGENTS.md` 更细，而且并非全项目适用
  3. 如果继续放在根 `AGENTS.md`，会导致根规则过重、过杂

必须特别关注的内容：
- 是否明确要求优先复用现有组件，而不是轻易新建
- 是否明确要求优先使用 BDL 和 BDL design tokens
- 是否明确要求先看 `lib/components` 的现有实现，再按需查 BDL 包内部
- 是否明确要求修改组件时同步考虑 `stories.tsx` 等联动文件
- 是否明确限制“机械地把 Figma 层级直接翻译成 DOM”
- 是否明确规定当信息不完整时的降级策略（先骨架、先复用、先占位，不要编造）

执行要求：
- 必须结合当前仓库的真实代码和真实规则文件进行判断，不要给泛泛建议
- 先 review，再设计，再决定是否修改
- 不要为了追求抽象上的完美而重构规则体系
- 优先保证规则稳定、易执行、便于后续迭代

输出格式：
1. 当前规则体系评审
2. 高优先级问题清单
3. 建议保留的规则
4. 建议修改或新增的规则
5. 是否建议新增 `lib/components/AGENTS.md`，以及原因
6. 如可安全落地，列出最小必要修改方案
7. 风险、假设与下一步建议



请基于本仓库的真实代码，专门评审并优化根目录 `AGENTS.md`。

要求：
- 先阅读 `AGENTS.md`
- 再阅读 `lib/components/` 下 3 到 5 个最有代表性的组件目录
- 从真实代码中提炼项目级、长期稳定、跨任务通用的硬约束
- 只修改应该放在根 `AGENTS.md` 的内容
- 不要把只适用于 Figma-to-code 的流程规则塞进根 `AGENTS.md`
- 不要默认扫描整个 `node_modules`；只有在现有组件看不出 BDL 用法时，才定向读取相关包

请重点判断：
- 当前 `AGENTS.md` 哪些条目过于泛化
- 哪些条目缺失
- 哪些条目应该更具体地约束 BDL 使用、组件复用、stories 联动修改、样式和 token 使用
- 哪些内容不该放在根 `AGENTS.md`

输出格式：
1. 当前 `AGENTS.md` 评审
2. 需要修改的条目
3. 建议新增的条目
4. 建议删除或下移的条目
5. 最小必要修改方案

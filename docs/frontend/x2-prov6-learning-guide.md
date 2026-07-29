# Ant Design X 2.0 + Pro v6 学习笔记

> 来源：[ant-design/x#1358](https://github.com/ant-design/x/issues/1358)（X 2.0 发布公告）、
> [ant-design/ant-design-pro#11735](https://github.com/ant-design/ant-design-pro/issues/11735)（Pro v6 发布公告）
> 及其实际源码（`app.tsx`、`requestErrorConfig.ts`、PR #11665 / #11693 / #11756 的 diff）。
> 整理日期：2026-07-29。AIERP 前端现状：antd 6.5 / X 2.9 / React Query 5 / Umi Max。

## 1. 两个公告的共同叙事

两个发布拼出了蚂蚁官方对 AI 时代中后台的完整技术选型：

| 层 | 旧栈（v5 时代） | 新栈（v6 时代） | AIERP 现状 |
|---|---|---|---|
| 组件库 | antd 5 + cssinjs | antd 6 + CSS Variables | ✅ antd 6.5 |
| AI 界面 | 手写 SSE + Bubble v1 | X 2.x monorepo（x / x-markdown / x-sdk） | ✅ X 2.9 + 自定义 Provider |
| 服务端状态 | ahooks `useRequest` | TanStack React Query | 🔄 逐页迁移中 |
| 构建 | webpack + mfsu | utoopack (Turbopack/Rust) | ✅ max dev/build |
| 样式 | Less | Tailwind v4 + antd-style + CSS Modules | 部分 |
| Lint | ESLint + Prettier | Biome | ❌ 仍 ESLint |

**共同方法论**：大版本升级官方推荐"新骨架 + 增量迁移业务代码"，而非原地硬升。
AIERP 的 PR #80（先升骨架）→ 逐页迁 React Query 的路径与官方建议一致。

## 2. X 2.0 架构拆解

### 2.1 Monorepo 拆分的意图

- `@ant-design/x` — 纯 UI（Bubble、Sender、ThoughtChain…）
- `@ant-design/x-markdown` — 流式 Markdown 渲染器（独立成包说明它是性能关键路径）
- `@ant-design/x-sdk` — 数据流（useXChat / useXConversations / ChatProvider / XRequest / XStream）

**核心模式：UI 与数据流彻底解耦。** `useXChat` 通过 `ChatProvider` 抽象把"协议适配"
（OpenAI / DeepSeek / 自定义后端）从"会话状态管理"（消息列表、loading、abort、fallback）中分离。
AIERP 的 `src/pages/ai/chat-provider.ts` 已正确落在这个模式上（`AbstractChatProvider`
三个钩子：`transformParams` / `transformLocalMessage` / `transformMessage`）。

### 2.2 AIERP 可利用的 X 2.x 能力

| 能力 | AIERP 状态 | 价值 |
|---|---|---|
| x-markdown 流式渲染（缓存/补全未完成语法） | ❌ Bubble 渲染纯文本 | 高 —— AI 输出含列表/表格/代码时体验质变 |
| Bubble 流式渲染变体 + 渲染动画 | ❌ | 中 |
| Actions（Copy / Feedback 预设） | ❌ | 高 —— Feedback 可回传后端做质量闭环 |
| ThoughtChain 思维链 | ❌ | 中 —— 可可视化后端 agents.py 多 Agent 中间步骤 |
| useXConversations 多会话 | ❌ 单会话 | 中。⚠️ 官方确认暂不支持触底加载/虚拟滚动 |
| Sources 引用 | ❌ | 低 —— 等 RAG 接入后才有意义 |
| 内置 OpenAIChatProvider | 自定义 Provider | 不适用 —— AIERP 后端是自定义 SSE 协议 |

### 2.3 评论区实战信息

- X 2.1.0+ 兼容 antd 5.x（部分语义化样式有差异）。
- V1 文档存档：`https://1-x-stable.ant-design-x.pages.dev/`，V1 进入半年维护期。
- MCP / 工具调用官方未答复 —— X 目前不含 tool-use 协议层，function calling 结果渲染需自己做。

## 3. Pro v6 源码级拆解

### 3.1 React Query 迁移模式（PR #11665，21 个页面）

| useRequest (ahooks) | React Query |
|---|---|
| `useRequest(fn)` | `useQuery({ queryKey, queryFn })` |
| `useRequest(fn, { manual: true })` | `useMutation({ mutationFn })` |
| `loading` | `isLoading`（query）/ `isPending`（mutation） |
| `run(params)` | `mutate(params)` |
| `refresh()` | `queryClient.invalidateQueries({ queryKey })` |

三个实战模式：

1. **纯查询页**：envelope 解包在 `queryFn` 里做（`.then((res) => res.data)`），
   组件拿到的 `data` 就是业务数据。
2. **变更 + 双刷新**：ProTable 的 `request` 属性是自带数据流，不走 React Query，
   所以官方代码里 `actionRef.current?.reload()` 与 `invalidateQueries` 并存。
   **ProTable 管理的列表不会被 invalidateQueries 刷新** —— 迁移时要认清这个边界。
3. **getInitialState 不走 React Query**：全局初始化在 React 树之外，用裸 request +
   `skipErrorHandler`，登录跳转保留原始 URL（`?redirect=`，#11722）。

### 3.2 错误处理管道（requestErrorConfig.ts + #11693）

三段式管道：

```
response → errorThrower (识别业务错误, 抛 BizError)
        → errorHandler  (按 showType 分发: SILENT/WARN/ERROR/NOTIFICATION/REDIRECT)
        → skipErrorHandler 逃生舱 (调用方自己处理)
```

**#11693 的核心教训**：responseInterceptor 里的 `message.error('请求失败！')` 与
errorHandler 的具体错误提示并存，用户看到两条错误。修复 = 清空 responseInterceptors。

> **错误提示必须有且只有一个出口。** 拦截器负责转换，errorHandler 负责提示。

其他：`data: any → unknown`；`REDIRECT` showType 补完（服务端可驱动前端跳转）。

### 3.3 离线容错（v6.0.1 #11756）

两个可直接移植的组件：

1. **OfflineBanner**（~40 行）：`useSyncExternalStore` 订阅 `online`/`offline` 事件，
   断网时顶部浮动 Alert。零依赖。
2. **离线感知 ErrorBoundary**：chunk 加载错误特征签名：

```ts
error.name === "ChunkLoadError"
  || /(?:loading|failed to load) (?:css )?chunk/i.test(error.message)
  || /Failed to fetch dynamically imported module/i.test(error.message)
```

chunk 错误 → "Retry" + "Reload"；普通渲染错误 → 通用错误页。通过 ProLayout 的
`ErrorBoundary` 属性替换默认边界，`rootContainer` 再包一层全局兜底。

### 3.4 PR 描述 ≠ 合并代码（打假）

#11693 的 PR 描述（AI 生成）声称添加 `staleTime: 30s` 和 `refetchOnWindowFocus: false`
全局默认值，但全仓搜索均无结果，`config.ts` 里是裸的 `reactQuery: {}`。

**教训**：AI 生成的 PR 描述会夸大变更内容，review 以 diff 为准。
**机会**：官方没做的全局默认值，我们在 `useApiQuery` 封装层自己做了（见第 5 节）。

### 3.5 杂项模式

- dayjs 插件集中初始化（`app.tsx` 一次 `dayjs.extend`，不散落各页面）。
- 菜单 `<Link prefetch>` + `routePrefetch` 配置，路由级预取。
- Cheatsheet：文档 Markdown 存 repo，用 x-markdown 渲染在应用内。

## 4. 已落地的行动（2026-07-29）

| 行动 | 来源 | 位置 |
|---|---|---|
| useApiQuery 增加 `keepPreviousData` 分页选项 | #11693 未落地的承诺 | `frontend/src/lib/queries.ts` |
| OfflineBanner 断网横幅 | #11756 | `frontend/src/ui/OfflineBanner.tsx` |
| ErrorBoundary chunk 错误识别 + 离线感知文案 | #11756 | `frontend/src/ui/ErrorBoundary.tsx` |
| QueryClient 全局默认值（staleTime 5min / retry 1 / refetchOnWindowFocus false） | #11693 | `frontend/src/lib/queryClient.ts`（此前已有） |

## 5. 后续候选

1. AI Chat 接入 `@ant-design/x-markdown`（Bubble content 换 XMarkdown，流式语法补全 + 代码高亮）。
2. Bubble 加 Actions.Copy / Actions.Feedback，Feedback 回传 `/api/v1/ai/feedback`。
3. 审计 `api/client.ts` + 页面 `message.error` 双重提示（#11693 教训）。
4. 登录跳转保留 redirect 参数检查（#11722）。
5. ThoughtChain 作为后端 Agent 中间步骤可视化候选。
6. 多会话（useXConversations）等需求明确再动 —— 官方无分页/虚拟滚动。

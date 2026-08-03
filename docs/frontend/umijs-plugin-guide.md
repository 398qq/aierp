# Umi plugin.ts 项目级插件指南

> 学习自 https://umijs.org/docs/guides/directory-structure#plugints
> 团队学习资源，与 `umijs-generator-guide.md` 配套

---

## 一、plugin.ts 是什么

`src/plugin.ts` 是**项目级 Umi 插件**，在**构建/编译时（Node 端）**运行，用于调用 Umi 插件 API 介入编译流程。它是纯 Node.js 代码，**不会在浏览器中执行**。

```ts
// src/plugin.ts
import type { IApi } from 'umi';

export default (api: IApi) => {
  api.onDevCompileDone((opts) => { /* 编译完成回调 */ });
  api.modifyHTML(($) => { /* cheerio 修改产物 HTML */ });
  api.chainWebpack((memo) => { /* 改 webpack 配置 */ });
};
```

---

## 二、三个配置入口的分工

| 文件 | 运行时机 | 适合放什么 |
|------|---------|-----------|
| `config/config.ts` / `.umirc.ts` | 构建时读取，纯**静态配置** | routes、proxy、title、插件开关、alias |
| `src/plugin.ts` | **构建/编译时**，Node 端代码逻辑 | 改 webpack 配置、修改产物 HTML、监听编译事件 |
| `src/app.ts` | **浏览器运行时** | `patchRoutes`、`rootContainer`、`getInitialState`、request 拦截器 |

> 一句话：**静态值进 config，编译期逻辑进 plugin.ts，浏览器期逻辑进 app.ts**。

### 典型误区

- ❌ 把 `patchRoutes`（浏览器路由）放进 `plugin.ts` — 这是 app.ts 的职责
- ❌ 把 request 拦截器放进 `plugin.ts` — 那是 app.ts 的 `requestInterceptors`
- ❌ 把 `getInitialState` 放进 `plugin.ts` — 是 app.ts 的职责，返回全局初始状态

---

## 三、IApi 常用方法速查

| 方法 | 作用 | 典型场景 |
|------|------|---------|
| `api.chainWebpack(fn)` | 修改 webpack 最终配置（chainWebpack 链式） | 添加 alias、loader、plugin |
| `api.modifyHTML(fn)` | 用 cheerio 修改产物 `index.html` | 注入 script、meta、构建信息 |
| `api.onDevCompileDone(fn)` | dev 编译完成时回调 | 打印提示信息、触发外部服务 |
| `api.registerCommand()` | 注册自定义 umi 命令 | 扩展 `umi dev/build/xxx` |
| `api.describe()` | 向插件市场声明插件 id 和描述 | 发布 npm 插件时需要 |
| `api.addRuntimePlugin()` | 注册运行时插件（会在浏览器执行） | 某些运行时增强 |

---

## 四、对 AIERP 的实际价值

当前 `frontend/src/` 下**没有** `plugin.ts` 和 `app.ts`，大多数需求用 config + 业务代码已能覆盖。以下是 plugin.ts 可能用得上的场景：

### 4.1 产物 HTML 注入构建信息（推荐优先实现）

方便前端报错时能定位到具体 Git commit，无需手动维护版本号：

```ts
// src/plugin.ts
import type { IApi } from 'umi';

export default (api: IApi) => {
  api.modifyHTML(($) => {
    $('body').append(`
      <script>
        window.__BUILD__ = {
          gitCommit: '${process.env.GIT_COMMIT ?? 'unknown'}',
          buildTime: '${new Date().toISOString()}',
        };
      </script>
    `);
    return $;
  });
};
```

`GIT_COMMIT` 通过 `.env` 或 CI pipeline 注入：
```bash
# .env.local
GIT_COMMIT=$(git rev-parse HEAD)
```

### 4.2 chainWebpack 加自定义配置

```ts
// src/plugin.ts
export default (api: IApi) => {
  api.chainWebpack((memo) => {
    // 给 HTML 注入资源加 hash
    memo.output.filename('static/js/[name].[contenthash:8].js');

    // 加自定义 alias
    memo.resolve.alias.set('@my', '/path/to/shared');
  });
};
```

> 优先用 `config/config.ts` 的 `alias`、`extraBabelPlugins`；这些够不着再上 `chainWebpack`。

### 4.3 dev 编译完成后打印提示

```ts
export default (api: IApi) => {
  api.onDevCompileDone(({ isFirstCompile }) => {
    if (isFirstCompile) {
      console.log('  ✅ AIERP Frontend ready  →  http://localhost:3002');
      console.log('  ✅ Backend health       →  http://localhost:8080/health');
    }
  });
};
```

---

## 五、app.ts（运行时配置）简介

与 plugin.ts 容易混淆，顺带说明。`src/app.ts` 的逻辑在**浏览器中运行**：

```ts
// src/app.ts
import { RequestConfig } from 'umi';

// 运行时全局初始状态
export async function getInitialState() {
  return { user: await fetchCurrentUser() };
}

// 统一 error 处理
export const errorHandler = (error: Error) => {
  if (error.message.includes('401')) {
    window.location.href = '/login';
  }
};

// request 配置
export const request: RequestConfig = {
  timeout: 10000,
  requestInterceptors: [(config) => { /* 注入 token */ return config; }],
  responseInterceptors: [(res) => { /* 统一处理 res.data */ return res; }],
};
```

AIERP 下一步如果要迁移 Zustand auth 到 Max 数据流体系，核心就是用 `app.ts` 的 `getInitialState` + `useModel('@@initialState')`，而不是 plugin.ts。

---

## 六、Umi 目录结构全表（AIERP 对照）

| 约定 | 作用 | AIERP 现状 |
|------|------|-----------|
| `config/config.ts` | 非运行时配置（`.umirc.ts` 优先级更高） | ✅ 已用，集中管理 |
| `.umirc.ts` | 配置文件，与 config.ts 二选一 | ❌ 未用，config.ts 够用 |
| `src/app.ts` | 运行时配置（浏览器端） | ❌ 未建，Zustand auth 目前在 store/ |
| `src/plugin.ts` | 项目级插件（Node 端编译时） | ❌ 未建，暂不需要 |
| `src/access.ts` | Max 权限定义 | ✅ 已有 |
| `src/global.ts` | 全局前置脚本 | ✅ 已有 |
| `src/global.(css\|less)` | 全局样式 | ⚠️ 在 `src/styles/`，可考虑归位 |
| `src/overrides.css` | 高优先级样式（自动加 `body` 前缀，覆盖 antd 等三方库） | ❌ 可选 |
| `src/layouts/index.tsx` | 全局布局约定 | ⚠️ 用配置式路由 + `ErpRouteLayout`，等效 |
| `src/pages/` | 约定式路由目录 | ⚠️ 配置式路由，两种模式不混用 |
| `src/pages/404.tsx` | 约定式路由下自动注册全局 404 | 配置式需手动配 `{ path: '*', component: 404 }` |
| `src/loading.tsx` | 页面切换全局 loading | ❌ 未建，可选 |
| `src/favicon.*` | 站点图标自动注入产物 | ⚠️ 检查是否已放 |
| `mock/` | Mock 数据目录 | ❌ 后端 FastAPI 真实响应，可选 |
| `public/` | 原样拷贝静态资源 | ✅ 正确用法 |
| `src/.umi/` / `src/.umi-production/` | dev/build 临时文件目录 | 勿提交 git（已在 .gitignore） |
| `.env` | 环境变量（PORT、UMI_ENV 等） | ⚠️ 可用 `UMI_ENV` 按环境加载不同配置 |
| `src/models/` | 声明式 Model（dva/Max 数据流） | ⚠️ 尚未使用，Zustand 在 store/ |
| `src/utils/` | 工具函数目录（推荐） | ⚠️ 在 `src/lib/`，可改名统一 |
| `src/services/` | API 服务层目录（推荐） | ⚠️ 在 `src/api/`，可改名统一 |

---

## 七、plugin.ts 与 app.ts 关系图

```
umi dev / umi build
    │
    ├─ config/config.ts        ← 静态配置（routes、proxy、plugins...）
    │
    ├─ src/plugin.ts            ← Node 端：webpack chain、modifyHTML、onDevCompileDone
    │                              （产物无关浏览器逻辑）
    │
    └─ 产物输出（dist/）
            │
            └─ index.html + static/js/*
                              │
                              └─ 浏览器加载
                                      │
                                      ├─ src/app.ts       ← 运行时：getInitialState、request、patchRoutes
                                      └─ src/access.ts    ← 权限校验
```

---

## 八、参考资源

- 官方文档：https://umijs.org/docs/guides/directory-structure
- 团队配套指南：`docs/frontend/umijs-generator-guide.md`
- Pro v6 迁移：`docs/frontend/pro-v6-migration-guide.md`
- 本项目 Umi 配置：`frontend/config/config.ts`
- 本项目 access：`frontend/src/access.ts`

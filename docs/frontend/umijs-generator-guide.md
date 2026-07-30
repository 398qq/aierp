# Umi Generator 学习指南

> 团队学习资源 — 来自官方文档 https://umijs.org/docs/guides/generator

## 一、Generator 是什么

Umi 内置**微生成器**（Micro Generator），通过 `umi g` 命令自动化生成重复性代码。

## 二、支持的 8 种 Generator

| Generator | 用途 | 常用度 |
|-----------|------|--------|
| **page** | 生成页面（.tsx + .less）| ⭐⭐⭐⭐⭐ |
| **component** | 生成组件（index.ts + component.tsx）| ⭐⭐⭐⭐ |
| **api** | 生成 RouteAPI 定义 | ⭐⭐⭐ |
| **mock** | 生成 Mock 数据 | ⭐⭐⭐ |
| **prettier** | 生成 Prettier 配置 | ⭐⭐ |
| **jest** | 生成 Jest 测试配置 | ⚠️ 本项目用 vitest，不适用 |
| **tailwindcss** | 生成 Tailwind 配置 | ⭐ |
| **dva** | 生成 DvaJS 状态管理 | ⭐ |
| **precommit** | 生成 Git precommit hook | ⭐ |

## 三、基本使用

```bash
# 交互式选择
$ umi g

# 直接指定
$ umi g <generatorName>
```

## 四、Page Generator（最常用）

### 用法

```bash
# 交互式
$ umi g page

# 直接生成（默认单文件模式）
$ umi g page foo
# 输出:
#   Write: src/pages/foo.tsx
#   Write: src/pages/foo.less

# 目录模式（更推荐）
$ umi g page bar --dir
# 输出:
#   Write: src/pages/bar/index.tsx
#   Write: src/pages/bar/index.less

# 嵌套路径
$ umi g page far/far/away/kingdom

# 批量
$ umi g page page1 page2 a/nested/page3

# 自定义参数
$ umi g page foo --msg "Hello" --count 10
```

### 预设变量

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `name` | - | 当前文件名 |
| `color` | - | 随机 RGB 颜色 |
| `cssExt` | `less` | 样式后缀 |

### 模板语法

```tsx
import './{{{name}}}.less'
const msg = '{{{msg}}}'
const count = {{{count}}}
```

3 个大括号 `{{{...}}}` 会被替换为实际值。

### 模板自定义

```bash
$ umi g page --eject
```

生成 `/templates/page/index.tsx.tpl` 和 `index.less.tpl`，之后 `umi g page` 会用你的模板。

## 五、Component Generator

```bash
# 交互式
$ umi g component

# 直接
$ umi g component foo
# 输出:
#   Write: src/components/Foo/index.ts
#   Write: src/components/Foo/component.tsx

# 嵌套
$ umi g component group/subgroup/baz

# 批量
$ umi g component apple banana orange
```

## 六、Mock Generator

```bash
$ umi g mock auth
# Write: mock/auth.ts

$ umi g mock users/profile
# Write: mock/users/profile.ts
```

## 七、Jest Generator ⚠️

```bash
$ umi g jest
# 询问: 是否使用 @testing-library/react?
# 输出:
#   Write package.json
#   Write jest.config.ts
```

**本项目用 vitest，不需要这个 generator**。Jest generator 生成的配置与本项目的 vitest.config.ts 冲突。

## 八、其他 Generator

### Prettier
```bash
$ umi g prettier
# 写入 package.json、.prettierrc、.prettierignore
```

### Tailwind CSS
```bash
$ umi g tailwindcss
# 写入 package.json、tailwind.config.js、tailwind.css
# 自动在 .umirc.ts / config/config.ts 中设置 tailwindcss plugin
```

### DvaJS
```bash
$ umi g dva
# 在 config 中启用 dva plugin，写入 example model
```

### Precommit
```bash
$ umi g precommit
# 写入 .lintstagedrc、.husky/、pre-commit、commit-msg
```

## 九、配置文件

在 `config/config.ts` 中自定义 generator：

```ts
export default {
  generators: {
    page: {
      templates: ['templates/page'],  // 自定义模板路径
    },
  },
};
```

## 十、Pro v6 项目中如何使用

### 推荐工作流

```bash
# 新建页面
$ npx umi g page customers/foo --dir
# 输出: src/pages/customers/foo/index.tsx
# 之后手动添加到 config/config.ts 路由

# 新建组件
$ npx umi g component common/BarChart
# 输出: src/components/common/BarChart/{index.ts, component.tsx}
```

### 建议：自定义 Pro v6 页面模板

```bash
$ npx umi g page --eject
# 编辑 templates/page/index.tsx.tpl
```

建议模板（ProCard + PageHeader 包装）：

```tsx
import { ProCard } from '@ant-design/pro-components';
import { PageHeader, StatusTag } from '@/ui';

export default function {{{name}}}() {
  return (
    <ProCard headerBordered title="{{{name}}}">
      <PageHeader title="{{{name}}}" />
    </ProCard>
  );
}
```

### 模板 cssExt 改 css

```bash
# 编辑 templates/page/index.less.tpl -> index.css.tpl
# 在 .umirc.ts 设置 cssExt: 'css'
```

## 十一、package.json 脚本

```json
{
  "scripts": {
    "new:page": "umi g page",
    "new:component": "umi g component",
    "new:mock": "umi g mock"
  }
}
```

## 十二、避坑

| 坑 | 解决 |
|---|------|
| 生成 .less 文件，本项目用 .css | 自定义模板或修改 cssExt |
| component 生成两个文件（index.ts + component.tsx）| eject 自定义或手动合并 |
| 模板变量 `{{{name}}}` 3 个大括号被替换 | 注意不要改成 `{{name}}` (2 个) |
| 在 pro v6 项目中混用 jest 和 vitest | 不要用 jest generator |

## 十三、参考资源

- 官方文档：https://umijs.org/docs/guides/generator
- 本项目 frontend/config/config.ts — Umi 配置
- docs/frontend/pro-v6-migration-guide.md — Pro v6 迁移指南

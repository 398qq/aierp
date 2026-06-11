// ESLint v9 flat config (Stage 5 Day 1)
// Run: npx eslint src/         # lint
//       npx eslint src/ --fix  # auto-fix

import js from "@eslint/js";
import tseslint from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";

export default [
  // Global ignores (keep in sync with .gitignore)
  {
    ignores: [
      "node_modules/**",
      "dist/**",
      "build/**",
      "coverage/**",
      "**/*.min.js",
      "src/test/setup.ts",  // vitest globals + localStorage stub
      "src/api/client.ts",  // axios interceptor (auto-generated pattern)
    ],
  },

  // Base JS rules
  js.configs.recommended,

  // TypeScript rules
  ...tseslint.configs.recommended,

  // React + TypeScript project
  {
    files: ["**/*.{ts,tsx}"],
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    languageOptions: {
      ecmaVersion: 2024,
      sourceType: "module",
      globals: {
        // Browser globals
        window: "readonly",
        document: "readonly",
        console: "readonly",
        setTimeout: "readonly",
        clearTimeout: "readonly",
        setInterval: "readonly",
        clearInterval: "readonly",
        fetch: "readonly",
        FormData: "readonly",
        URL: "readonly",
        URLSearchParams: "readonly",
        localStorage: "readonly",
        sessionStorage: "readonly",
        // React 19
        React: "readonly",
        // Vite
        import: "readonly",
        // Node (vitest config)
        process: "readonly",
        Buffer: "readonly",
      },
    },
    rules: {
      // React Hooks rules
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",

      // React Refresh (HMR)
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true },
      ],

      // TypeScript — relax a bit for a React 19 + antd project
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      "@typescript-eslint/no-explicit-any": "warn",  // 避免老代码全报
      "@typescript-eslint/no-empty-object-type": "off",  // {} types allowed
      "@typescript-eslint/no-namespace": "off",  // some legacy uses

      // General JS — relax for fast iteration
      "no-console": "off",  // console.log widely used for debug
      "no-debugger": "warn",
      "no-unused-vars": "off",  // covered by @typescript-eslint
      "no-empty": ["warn", { allowEmptyCatch: true }],
    },
  },

  // Test files (vitest globals)
  {
    files: ["src/test/**/*.{ts,tsx}", "**/*.test.{ts,tsx}"],
    languageOptions: {
      globals: {
        describe: "readonly",
        it: "readonly",
        test: "readonly",
        expect: "readonly",
        beforeEach: "readonly",
        afterEach: "readonly",
        beforeAll: "readonly",
        afterAll: "readonly",
        vi: "readonly",
        vitest: "readonly",
        globalThis: "readonly",
      },
    },
    rules: {
      "@typescript-eslint/no-explicit-any": "off",  // tests use any for mocks
      "react-refresh/only-export-components": "off",  // tests export helpers
    },
  },
];

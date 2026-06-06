/**
 * Design Tokens — single source of truth for the AIERP frontend.
 *
 * Merged into antd `ConfigProvider.theme` and used directly by components
 * that need a value outside antd's theme (e.g. inline gradients, custom
 * charts). Two scopes:
 *
 *   1. `brand.*`  — marketing surfaces (landing, inquiry portal, brand showcase)
 *   2. `app.*`    — operational app shell (customers, sales, inventory, …)
 *
 * Rule of thumb: app screens import from `app`; landing pages from `brand`.
 * Never reach for hex codes in components — import here instead.
 *
 * Mirror in DESIGN.md. Update both together.
 */

export const brand = {
  primary: "#533afd",
  primaryDeep: "#4434d4",
  primaryPress: "#2e2b8c",
  primarySoft: "#665efd",
  primaryBgSubduedHover: "#b9b9f9",
  brandDark900: "#1c1e54",
  ink: "#0d253d",
  inkSecondary: "#273951",
  inkMute: "#64748d",
  inkMute2: "#61718a",
  onPrimary: "#ffffff",
  canvas: "#ffffff",
  canvasSoft: "#f6f9fc",
  canvasCream: "#f5e9d4",
  hairline: "#e3e8ee",
  hairlineInput: "#a8c3de",
  ruby: "#ea2261",
  magenta: "#f96bee",
  lemon: "#9b6829",
  shadowBlue: "#003770",
} as const;

export const app = {
  canvas: "#ffffff",
  workspace: "#f6f9fc",
  sider: "#1c1e54",
  siderItemActive: "#533afd",
  header: "#ffffff",
  contentMaxWidth: 1440,
  contentPadding: 24,
  cardPadding: 16,
  rowHeight: 44,
  rowHeightCompact: 36,
  rowHeightComfort: 52,
  headerHeight: 56,
  siderWidth: 220,
  siderWidthCollapsed: 64,
} as const;

export const semantic = {
  success: "#10b981",
  successBg: "#ecfdf5",
  warning: "#f59e0b",
  warningBg: "#fffbeb",
  danger: "#ef4444",
  dangerBg: "#fef2f2",
  info: "#3b82f6",
  infoBg: "#eff6ff",
  processing: "#eab308",
  neutral: "#64748b",
  neutralBg: "#f1f5f9",
  moneyPositive: "#10b981",
  moneyNegative: "#ef4444",
  hairline: brand.hairline,
} as const;

export const space = {
  s4: 4,
  s8: 8,
  s12: 12,
  s16: 16,
  s24: 24,
  s32: 32,
  s48: 48,
  s64: 64,
} as const;

export const radius = {
  pill: 999,
  card: 8,
  input: 6,
  tag: 4,
  none: 0,
} as const;

export const fontSize = {
  displayXxl: 56,
  displayXl: 48,
  displayLg: 32,
  displayMd: 26,
  headingLg: 22,
  headingMd: 20,
  headingSm: 18,
  bodyLg: 16,
  bodyMd: 15,
  body: 14,
  bodySm: 13,
  caption: 12,
  numeric: 14,
} as const;

export const fontWeight = {
  light: 300,
  regular: 400,
  medium: 500,
  semibold: 600,
  bold: 700,
} as const;

export const fontFeature = {
  tabularNums: '"tnum"',
  stylistic01: '"ss01"',
} as const;

export const motion = {
  fast: "120ms cubic-bezier(0.4, 0, 0.2, 1)",
  base: "200ms cubic-bezier(0.4, 0, 0.2, 1)",
  slow: "320ms cubic-bezier(0.4, 0, 0.2, 1)",
} as const;

export const shadow = {
  card: "0 1px 2px rgba(15, 23, 42, 0.04), 0 1px 3px rgba(15, 23, 42, 0.06)",
  dropdown:
    "0 4px 6px -1px rgba(15, 23, 42, 0.08), 0 2px 4px -2px rgba(15, 23, 42, 0.06)",
  modal:
    "0 10px 15px -3px rgba(15, 23, 42, 0.08), 0 4px 6px -4px rgba(15, 23, 42, 0.06)",
  popover:
    "0 4px 16px rgba(15, 23, 42, 0.08), 0 1px 2px rgba(15, 23, 42, 0.04)",
} as const;

/**
 * Status → tone mapping for `<StatusTag tone="...">`.
 * Use this in pages that map enum values to colors instead of
 * defining per-page constants.
 */
export const statusTone = {
  draft: "info",
  pending: "info",
  in_progress: "processing",
  processing: "processing",
  active: "processing",
  confirmed: "info",
  shipped: "processing",
  partial: "warning",
  completed: "success",
  paid: "success",
  received: "success",
  done: "success",
  approved: "success",
  warning: "warning",
  expiring: "warning",
  overdue: "danger",
  rejected: "danger",
  cancelled: "danger",
  failed: "danger",
  inactive: "neutral",
  archived: "neutral",
  disabled: "neutral",
} as const;

export type StatusToneKey = keyof typeof statusTone;
export type AppTone = (typeof statusTone)[StatusToneKey];

/**
 * Convenience: antd theme object. Pass to `<ConfigProvider theme={antdTheme}>`.
 * The app shell is a light theme; the marketing pages can swap to `brandTheme`.
 */
export const antdTheme = {
  token: {
    colorPrimary: brand.primary,
    colorSuccess: semantic.success,
    colorWarning: semantic.warning,
    colorError: semantic.danger,
    colorInfo: semantic.info,
    colorLink: brand.primary,
    colorText: brand.ink,
    colorTextSecondary: brand.inkSecondary,
    colorTextTertiary: brand.inkMute,
    colorBorder: brand.hairline,
    colorBgContainer: app.canvas,
    colorBgLayout: app.workspace,
    colorBgElevated: app.canvas,
    borderRadius: radius.card,
    borderRadiusSM: radius.input,
    borderRadiusXS: radius.tag,
    borderRadiusLG: radius.card,
    fontFamily:
      "'SF Pro Display', system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif",
    fontSize: fontSize.body,
    fontSizeLG: fontSize.bodyLg,
    fontSizeSM: fontSize.bodySm,
    controlHeight: 36,
    controlHeightLG: 40,
    controlHeightSM: 28,
    motionDurationFast: motion.fast,
    motionDurationMid: motion.base,
    motionDurationSlow: motion.slow,
  },
  components: {
    Layout: {
      headerBg: app.header,
      headerHeight: app.headerHeight,
      headerPadding: `0 ${app.contentPadding}px`,
      siderBg: app.sider,
      bodyBg: app.workspace,
    },
    Menu: {
      darkItemBg: app.sider,
      darkItemSelectedBg: app.siderItemActive,
      darkItemHoverBg: "rgba(255, 255, 255, 0.06)",
    },
    Table: {
      headerBg: app.workspace,
      headerSplitColor: brand.hairline,
      rowHoverBg: app.workspace,
      cellPaddingBlock: 12,
      cellPaddingInline: 12,
    },
    Button: {
      borderRadius: radius.pill,
      borderRadiusLG: radius.pill,
      borderRadiusSM: radius.pill,
      controlHeight: 36,
      paddingInline: 16,
    },
    Tag: {
      borderRadiusSM: radius.tag,
    },
    Drawer: {
      paddingLG: app.cardPadding,
    },
    Card: {
      borderRadiusLG: radius.card,
    },
  },
} as const;

/**
 * Helper: numeric CSS for money / date / quantity cells.
 * Apply via `style={numericStyle}` on `<span>` / `<Typography.Text>`.
 */
export const numericStyle = {
  fontFeatureSettings: `"tnum" 1, ${fontFeature.stylistic01} 1`,
  fontVariantNumeric: "tabular-nums",
} as const;

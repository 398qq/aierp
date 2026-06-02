/**
 * Stripe-inspired Ant Design 6 theme.
 * Extracted from DESIGN.md Stripe design analysis.
 */

export const stripeTheme = {
  token: {
    // ── Brand ──
    colorPrimary: "#533afd",
    colorPrimaryHover: "#665efd",
    colorPrimaryActive: "#4434d4",
    colorPrimaryBg: "#f0edff",
    colorPrimaryBgHover: "#e3deff",

    // ── Text ──
    colorText: "#0d253d",
    colorTextSecondary: "#273951",
    colorTextTertiary: "#64748d",
    colorTextQuaternary: "#94a3b8",
    colorTextPlaceholder: "#94a3b8",

    // ── Backgrounds ──
    colorBgBase: "#ffffff",
    colorBgContainer: "#f6f9fc",
    colorBgElevated: "#ffffff",
    colorBgLayout: "#f6f9fc",
    colorBgSpotlight: "#533afd",
    colorBgMask: "rgba(13,37,61,0.45)",

    // ── Borders ──
    colorBorder: "#e3e8ee",
    colorBorderSecondary: "#edf2f7",

    // ── Fill (background for disabled, etc) ──
    colorFillTertiary: "#f1f5f9",
    colorFillQuaternary: "#f8fafc",

    // ── Success / Error / Warning ──
    colorSuccess: "#2dd4a0",
    colorSuccessBg: "#e6faf4",
    colorError: "#ea2261",
    colorErrorBg: "#fde8ef",
    colorWarning: "#f59e0b",
    colorWarningBg: "#fef3c7",
    colorInfo: "#533afd",
    colorInfoBg: "#f0edff",

    // ── Radius ──
    borderRadius: 4,
    borderRadiusLG: 8,
    borderRadiusSM: 3,
    borderRadiusXS: 2,

    // ── Font ──
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    fontFamilyCode: "'JetBrains Mono', 'SF Mono', ui-monospace, monospace",
    fontSize: 14,
    fontSizeHeading1: 26,
    fontSizeHeading2: 22,
    fontSizeHeading3: 18,
    fontSizeHeading4: 16,

    // ── Line Height ──
    lineHeight: 1.5,
    lineHeightHeading1: 1.2,
    lineHeightHeading2: 1.3,
    lineHeightHeading3: 1.4,

    // ── Control ──
    controlHeight: 34,
    controlHeightSM: 28,
    controlHeightLG: 40,
    controlOutlineWidth: 1,
    controlOutline: "rgba(83,58,253,0.15)",

    // ── Spacing ──
    marginXXS: 2,
    marginXS: 4,
    marginSM: 8,
    marginMD: 12,
    marginLG: 16,
    marginXL: 24,
    paddingXXS: 2,
    paddingXS: 4,
    paddingSM: 8,
    paddingMD: 12,
    paddingLG: 16,
    paddingXL: 24,

    // ── Shadow ──
    boxShadow: "0 1px 3px 0 rgba(0,0,0,0.04), 0 1px 2px 0 rgba(0,0,0,0.03)",
    boxShadowSecondary:
      "0 4px 12px 0 rgba(0,0,0,0.06), 0 1px 3px 0 rgba(0,0,0,0.04)",
  },
  components: {
    Button: {
      borderRadius: 9999,
      borderRadiusLG: 9999,
      borderRadiusSM: 9999,
      controlHeight: 36,
      controlHeightSM: 30,
      controlHeightLG: 44,
      paddingContentHorizontal: 18,
      paddingContentHorizontalSM: 14,
      paddingContentHorizontalLG: 24,
      fontWeight: 500,
    },
    Card: {
      borderRadius: 8,
      borderRadiusLG: 8,
      colorBgContainer: "#ffffff",
      boxShadow: "0 1px 3px 0 rgba(0,0,0,0.04), 0 1px 2px 0 rgba(0,0,0,0.03)",
      boxShadowTertiary:
        "0 1px 3px 0 rgba(0,0,0,0.04), 0 1px 2px 0 rgba(0,0,0,0.03)",
    },
    Table: {
      borderRadius: 8,
      colorBgContainer: "#ffffff",
      headerBg: "#f8fafc",
      headerColor: "#273951",
      headerSortActiveBg: "#edf2f7",
      headerSortHoverBg: "#edf2f7",
      rowHoverBg: "#f1f5f9",
      borderColor: "#e3e8ee",
    },
    Tag: {
      borderRadius: 4,
      lineHeight: 1.4,
    },
    Input: {
      borderRadius: 4,
      borderRadiusLG: 6,
      controlHeight: 36,
      controlHeightSM: 30,
      controlHeightLG: 44,
    },
    Select: {
      borderRadius: 4,
      borderRadiusLG: 6,
      controlHeight: 36,
      controlHeightSM: 30,
      controlHeightLG: 44,
    },
    DatePicker: {
      borderRadius: 4,
      borderRadiusLG: 6,
      controlHeight: 36,
      controlHeightSM: 30,
    },
    Modal: {
      borderRadius: 10,
      borderRadiusLG: 10,
      boxShadow:
        "0 12px 40px 0 rgba(0,0,0,0.12), 0 1px 4px 0 rgba(0,0,0,0.06)",
    },
    Dropdown: {
      borderRadius: 6,
      borderRadiusLG: 6,
      boxShadow:
        "0 4px 12px 0 rgba(0,0,0,0.08), 0 1px 3px 0 rgba(0,0,0,0.04)",
    },
    Tabs: {
      inkBarColor: "#533afd",
      itemColor: "#64748d",
      itemHoverColor: "#0d253d",
      itemSelectedColor: "#533afd",
    },
    Progress: {
      defaultColor: "#533afd",
      successColor: "#2dd4a0",
    },
    Switch: {
      colorPrimary: "#533afd",
    },
  },
} as const;

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Form, Input, App as AntdApp } from "antd";
import { useAuthStore } from "../../store/auth";

export default function Login() {
  const [loading, setLoading] = useState(false);
  const { message } = AntdApp.useApp();
  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      await login(values.username, values.password);
      message.success("登录成功");
      navigate("/");
    } catch (error: unknown) {
      const loginError = error as { response?: { data?: { msg?: string } }; message?: string };
      message.error(loginError.response?.data?.msg || loginError.message || "用户名或密码错误");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <style>{`
        .login-root {
          display: grid;
          grid-template-columns: 420px 1fr;
          height: 100vh;
          font-family: system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
          background: #FFFFFF;
        }

        @media (max-width: 768px) {
          .login-root {
            grid-template-columns: 1fr;
            grid-template-rows: auto 1fr;
          }
          .login-brand {
            min-height: 200px;
            padding: 40px 32px;
          }
          .login-brand-headline {
            font-size: 26px !important;
          }
          .login-brand-center {
            padding: 24px 0;
          }
          .login-form-panel {
            padding: 40px 32px;
          }
        }

        /* ── Brand panel ── */
        .login-brand {
          background: #10233f;
          color: #FFFFFF;
          padding: 52px 48px;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
        }

        .login-logo-row {
          display: flex;
          align-items: center;
          gap: 14px;
        }

        .login-logo-mark {
          width: 38px;
          height: 38px;
          background: #2563eb;
          border-radius: 6px;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }

        .login-logo-name {
          font-family: inherit;
          font-size: 20px;
          font-weight: 600;
          letter-spacing: -0.02em;
          color: #FFFFFF;
          line-height: 1.2;
        }

        .login-logo-sub {
          font-size: 10px;
          font-weight: 400;
          color: rgba(255,255,255,0.32);
          letter-spacing: 0.14em;
          text-transform: uppercase;
          margin-top: 2px;
        }

        .login-brand-center {
          flex: 1;
          display: flex;
          flex-direction: column;
          justify-content: center;
          padding: 40px 0;
        }

        .login-brand-headline {
          font-family: inherit;
          font-size: 40px;
          font-weight: 700;
          line-height: 1.12;
          color: #FFFFFF;
          margin-bottom: 28px;
          letter-spacing: -0.025em;
        }

        .login-brand-headline em {
          font-style: italic;
          color: #93c5fd;
        }

        .login-brand-sub {
          font-size: 13px;
          font-weight: 300;
          line-height: 1.85;
          color: rgba(255,255,255,0.68);
          max-width: 268px;
        }

        .login-brand-footer {
          font-size: 10px;
          color: rgba(255,255,255,0.16);
          letter-spacing: 0.04em;
        }

        /* ── Form panel ── */
        .login-form-panel {
          background: #FFFFFF;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 48px;
        }

        .login-form-wrap {
          width: 100%;
          max-width: 300px;
        }

        .login-form-heading {
          font-size: 10px;
          font-weight: 500;
          letter-spacing: 0.14em;
          text-transform: uppercase;
          color: #6B6B6B;
          margin-bottom: 36px;
        }

        .login-rule {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 36px;
        }

        .login-rule-dot {
          width: 4px;
          height: 4px;
          border-radius: 50%;
          background: #E0E0E0;
        }

        .login-rule-dot-accent {
          width: 26px;
          height: 26px;
          border-radius: 50%;
          background: #2563eb;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .login-rule-dot-accent::after {
          content: '';
          width: 9px;
          height: 9px;
          border-radius: 50%;
          background: #FFFFFF;
        }

        /* ── Antd form overrides ── */
        .login-form .ant-form-item {
          margin-bottom: 28px;
        }

        .login-form .ant-form-item-label {
          padding: 0 0 6px 0;
        }

        .login-form .ant-form-item-label > label {
          font-size: 11px;
          font-weight: 400;
          color: #6B6B6B;
          letter-spacing: 0.02em;
          height: auto;
        }

        .login-form .ant-input-affix-wrapper {
          border: none !important;
          border-bottom: 1px solid #DEDEDE !important;
          border-radius: 0 !important;
          padding: 0 0 10px 0 !important;
          box-shadow: none !important;
          background: transparent !important;
          font-size: 15px !important;
          font-weight: 300 !important;
          color: #0F0F0F !important;
          font-family: inherit !important;
        }

        .login-form .ant-input-affix-wrapper:focus,
        .login-form .ant-input-affix-wrapper-focused {
          border-bottom-color: #2563eb !important;
          border-bottom-width: 1.5px !important;
          box-shadow: none !important;
        }

        .login-form .ant-input {
          font-size: 15px;
          font-weight: 300;
          color: #172033;
          background: transparent;
        }

        .login-form .ant-input::placeholder {
          color: rgba(107,107,107,0.38);
        }

        .login-form .ant-input-prefix {
          color: #6B6B6B;
          margin-right: 8px;
        }

        .login-form .ant-input-password-icon {
          color: #6B6B6B !important;
        }

        .login-submit {
          width: 100%;
          height: 50px;
          background: #2563eb;
          border: none;
          border-radius: 2px;
          font-family: inherit;
          font-size: 12px;
          font-weight: 400;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          color: #FFFFFF;
          cursor: pointer;
          margin-top: 8px;
          transition: background 0.18s, transform 0.08s;
          position: relative;
          overflow: hidden;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .login-submit:hover:not(:disabled) {
          background: #1d4ed8;
        }

        .login-submit:active:not(:disabled) {
          transform: scale(0.99);
        }

        .login-submit:disabled {
          background: #B8B8B8;
          cursor: not-allowed;
        }

        .login-loading-bar {
          position: absolute;
          left: 0;
          top: 0;
          height: 2px;
          background: rgba(255,255,255,0.4);
          width: 0;
          animation: loginBar 1.2s ease-in-out infinite;
        }

        @keyframes loginBar {
          0%   { width: 0; left: 0; }
          50%  { width: 55%; left: 22%; }
          100% { width: 0; left: 100%; }
        }

        .login-form-footer {
          margin-top: 56px;
          font-size: 10px;
          color: rgba(107,107,107,0.38);
          text-align: center;
          letter-spacing: 0.04em;
        }
      `}</style>

      <div className="login-root">
        {/* ── Left brand panel ── */}
        <div className="login-brand">
          <div className="login-logo-row">
            <div className="login-logo-mark">
              <svg viewBox="0 0 22 22" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="2" y="2" width="8" height="8" rx="1.5" fill="#FFFFFF"/>
                <rect x="12" y="2" width="8" height="8" rx="1.5" fill="#FFFFFF" opacity="0.72"/>
                <rect x="2" y="12" width="8" height="8" rx="1.5" fill="#FFFFFF" opacity="0.72"/>
                <rect x="12" y="12" width="8" height="8" rx="1.5" fill="#FFFFFF" opacity="0.42"/>
              </svg>
            </div>
            <div>
              <div className="login-logo-name">AIERP</div>
              <div className="login-logo-sub">Intelligent Distribution</div>
            </div>
          </div>

          <div className="login-brand-center">
            <h1 className="login-brand-headline">
              智能分销<br/>
              <em>重新定义</em><br/>
              元器件贸易
            </h1>
            <p className="login-brand-sub">
              AI 驱动的电子元器件全链路管理系统。<br/>
              商机洞察 · 库存优化 · 供应商协同
            </p>
          </div>

          <div className="login-brand-footer">
            © 2025 AIERP · Electronic Component Distribution Platform
          </div>
        </div>

        {/* ── Right form panel ── */}
        <div className="login-form-panel">
          <div className="login-form-wrap">
              <div className="login-form-heading">登录 AIERP 运营平台</div>

            <div className="login-rule">
              <div className="login-rule-dot-accent"/>
              <div className="login-rule-dot"/>
              <div className="login-rule-dot"/>
            </div>

            <Form
              className="login-form"
              layout="vertical"
              onFinish={onFinish}
              size="large"
            >
              <Form.Item
                name="username"
                rules={[{ required: true, message: "请输入用户名" }]}
              >
                <Input
                  prefix={<span style={{ color: "#6B6B6B", fontSize: 13 }}>◼</span>}
                  placeholder="admin"
                  autoComplete="username"
                  spellCheck={false}
                />
              </Form.Item>

              <Form.Item
                name="password"
                rules={[{ required: true, message: "请输入密码" }]}
              >
                <Input.Password
                  prefix={<span style={{ color: "#6B6B6B", fontSize: 13 }}>◼</span>}
                  placeholder="••••••••"
                  autoComplete="current-password"
                />
              </Form.Item>

              <Form.Item style={{ marginBottom: 0 }}>
                <button
                  type="submit"
                  className="login-submit"
                  disabled={loading}
                >
                  {loading && <span className="login-loading-bar"/>}
                  {loading ? "正在登录…" : "登录"}
                </button>
              </Form.Item>
            </Form>

            <div className="login-form-footer">
              AIERP · 智能电子元器件分销管理系统
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

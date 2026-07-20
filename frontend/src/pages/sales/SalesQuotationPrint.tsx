import type { Quotation } from "../../types";
import { SalesPrintPortal } from "./SalesPrintPortal";
import "./salesDocumentPrint.css";

const SELLER_NAME = "深圳天允电子有限公司";
const STATUS: Record<string, string> = {
  draft: "草稿",
  sent: "已发送",
  accepted: "客户已接受",
  won: "已成交",
  lost: "已失效",
  expired: "已过期",
};

function date(value: string | null | undefined) {
  return value ? value.slice(0, 10) : "-";
}

function amount(value: number | null | undefined, currency = "CNY", maximumFractionDigits = 2) {
  const symbols: Record<string, string> = { CNY: "¥", USD: "$", EUR: "€", HKD: "HK$" };
  return `${symbols[currency] || `${currency} `}${Number(value || 0).toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits,
  })}`;
}

export function SalesQuotationPrint({ quote, customerName }: { quote: Quotation; customerName: string }) {
  const buyer = customerName || quote.customer_name || `客户 #${quote.customer_id}`;
  const quantity = quote.items.reduce((sum, item) => sum + Number(item.quantity || 0), 0);
  const untaxed = quote.items.reduce((sum, item) => {
    const gross = Number(item.total_price || 0);
    const rate = Number(item.tax_rate || 0) / 100;
    return sum + (rate > 0 ? gross / (1 + rate) : gross);
  }, 0);
  const gross = Number(quote.total_amount || 0);
  const tax = Math.max(gross - untaxed, 0);

  return (
    <SalesPrintPortal><section className="sales-document-print" data-testid="sales-quotation-print" aria-label="销售报价单打印单据">
      {quote.status === "draft" && <div className="sales-print-watermark">草稿 · 非正式报价</div>}
      {(quote.status === "lost" || quote.status === "expired") && <div className="sales-print-watermark sales-print-watermark-danger">已失效</div>}

      <header className="sales-print-header">
        <div className="sales-print-brand"><strong>{SELLER_NAME}</strong><span>TIANYUN ELECTRONICS · QUOTATION</span></div>
        <div className="sales-print-title"><h1>销售报价单</h1><span>SALES QUOTATION</span></div>
        <div className="sales-print-control">
          <span>报价编号</span><strong>{quote.quotation_no || `QT-${quote.id}`}</strong>
          <span>报价状态</span><strong>{STATUS[quote.status] || quote.status}</strong>
          <span>报价日期</span><strong>{date(quote.created_at)}</strong>
        </div>
      </header>

      <section className="sales-print-section">
        <h2><span>01</span> 报价对象</h2>
        <div className="sales-print-party-grid">
          <div className="sales-print-label">客户名称</div><div className="sales-print-party-name">{buyer}</div>
          <div className="sales-print-label">报价单位</div><div className="sales-print-party-name">{SELLER_NAME}</div>
          <div className="sales-print-label">报价主题</div><div>{quote.title || "产品销售报价"}</div>
          <div className="sales-print-label">关联商机</div><div>{quote.opportunity_title || (quote.opportunity_id ? `#${quote.opportunity_id}` : "-")}</div>
        </div>
      </section>

      <section className="sales-print-section">
        <h2><span>02</span> 商务信息</h2>
        <div className="sales-print-meta">
          <div><span>报价有效期</span><strong>{date(quote.valid_until)}</strong></div>
          <div><span>结算币种</span><strong>{quote.currency || "CNY"}</strong></div>
          <div><span>贸易条款</span><strong>{quote.incoterms || "-"}</strong></div>
          <div><span>付款条件</span><strong>{quote.payment_terms || "-"}</strong></div>
          <div><span>整单折扣</span><strong>{quote.discount_rate == null ? "-" : `${quote.discount_rate}%`}</strong></div>
          <div><span>折扣金额</span><strong>{amount(quote.discount_amount, quote.currency)}</strong></div>
          <div className="wide"><span>报价备注</span><strong>{quote.notes || "-"}</strong></div>
        </div>
      </section>

      <section className="sales-print-section">
        <h2><span>03</span> 报价明细</h2>
        <table className="sales-print-table quotation-items">
          <thead><tr><th>#</th><th>产品名称 / 规格</th><th>单位</th><th className="number">数量</th><th className="number">含税单价</th><th>生产批次</th><th>交期</th><th className="number">税率</th><th className="number">价税合计</th><th>备注</th></tr></thead>
          <tbody>{quote.items.map((item, index) => (
            <tr key={item.id}>
              <td>{index + 1}</td>
              <td><strong>{item.product_name || "-"}</strong><small>{item.product_id ? `产品 #${item.product_id}` : ""}</small></td>
              <td>{item.unit || "-"}</td>
              <td className="number">{Number(item.quantity || 0).toLocaleString("zh-CN")}</td>
              <td className="number">{amount(item.unit_price, quote.currency, 6)}</td>
              <td>{item.datecode || "-"}</td>
              <td>{item.lead_time || "-"}</td>
              <td className="number">{item.tax_rate == null ? "-" : `${item.tax_rate}%`}</td>
              <td className="number"><strong>{amount(item.total_price, quote.currency)}</strong></td>
              <td>{item.notes || "-"}</td>
            </tr>
          ))}</tbody>
          <tfoot><tr><td colSpan={3}>合计</td><td className="number"><strong>{quantity.toLocaleString("zh-CN")}</strong></td><td colSpan={4} /><td className="number"><strong>{amount(quote.total_amount, quote.currency)}</strong></td><td /></tr></tfoot>
        </table>
        <div className="sales-print-totals">
          <div><span>未税金额</span><strong>{amount(untaxed, quote.currency)}</strong></div>
          <div><span>税额</span><strong>{amount(tax, quote.currency)}</strong></div>
          <div className="grand"><span>价税合计</span><strong>{amount(quote.total_amount, quote.currency)}</strong></div>
        </div>
      </section>

      <section className="sales-print-section sales-print-terms">
        <h2><span>04</span> 报价说明</h2>
        <ol>
          <li>本报价所列产品、数量、单价、税率及交期以双方最终书面确认为准。</li>
          <li>报价有效期截至 {date(quote.valid_until)}；超过有效期后，价格与交期需重新确认。</li>
          <li>产品包装、运输、验收、质保及付款事项按本报价、后续销售合同或订单约定执行。</li>
        </ol>
      </section>

      <section className="sales-print-signatures">
        <div><h3>客户确认</h3><strong>{buyer}</strong><p>授权代表：________________</p><p>签章：____________________</p><p>日期：____年__月__日</p></div>
        <div><h3>报价单位</h3><strong>{SELLER_NAME}</strong><p>业务代表：________________</p><p>签章：____________________</p><p>日期：____年__月__日</p></div>
      </section>
      <footer className="sales-print-footer"><span>{quote.quotation_no || `QT-${quote.id}`}</span><span>销售报价单 · ERP 系统生成</span><span>报价正文</span></footer>
    </section></SalesPrintPortal>
  );
}

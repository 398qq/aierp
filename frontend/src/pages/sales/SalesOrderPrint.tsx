import type { SalesOrder } from "../../types";
import { SalesPrintPortal } from "./SalesPrintPortal";
import "./salesDocumentPrint.css";

const SELLER_NAME = "深圳天允电子有限公司";
const STATUS: Record<string, string> = {
  draft: "草稿",
  pending: "待确认",
  confirmed: "已确认",
  shipped: "已发货",
  delivered: "已签收",
  cancelled: "已取消",
};

function date(value: string | null | undefined) {
  return value ? value.slice(0, 10) : "-";
}

function amount(value: number | null | undefined, currency = "CNY", digits = 2) {
  const symbols: Record<string, string> = { CNY: "¥", USD: "$", EUR: "€", HKD: "HK$" };
  return `${symbols[currency] || `${currency} `}${Number(value || 0).toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: digits,
  })}`;
}

export function SalesOrderPrint({ order }: { order: SalesOrder }) {
  const quantity = order.items.reduce((sum, item) => sum + Number(item.quantity || 0), 0);
  const untaxed = order.items.reduce((sum, item) => {
    const total = Number(item.total_price || 0);
    const rate = Number(item.tax_rate || 0) / 100;
    return sum + (rate ? total / (1 + rate) : total);
  }, 0);
  const tax = Math.max(Number(order.total_amount || 0) - untaxed, 0);

  return (
    <SalesPrintPortal><section className="sales-document-print" data-testid="sales-order-print" aria-label="销售订单打印单据">
      {order.status === "draft" && <div className="sales-print-watermark">草稿 · 非正式订单</div>}
      {order.status === "cancelled" && <div className="sales-print-watermark sales-print-watermark-danger">已取消</div>}

      <header className="sales-print-header">
        <div className="sales-print-brand"><strong>{SELLER_NAME}</strong><span>TIANYUN ELECTRONICS · SALES</span></div>
        <div className="sales-print-title"><h1>销售订单</h1><span>SALES ORDER</span></div>
        <div className="sales-print-control">
          <span>订单编号</span><strong>{order.order_no || `SO-${order.id}`}</strong>
          <span>订单状态</span><strong>{STATUS[order.status] || order.status}</strong>
          <span>制单日期</span><strong>{date(order.order_date || order.created_at)}</strong>
        </div>
      </header>

      <section className="sales-print-section">
        <h2><span>01</span> 交易双方</h2>
        <div className="sales-print-party-grid">
          <div className="sales-print-label">甲方 / 采购方</div><div className="sales-print-party-name">{order.customer_name || `客户 #${order.customer_id}`}</div>
          <div className="sales-print-label">乙方 / 销售方</div><div className="sales-print-party-name">{SELLER_NAME}</div>
          <div className="sales-print-label">收货地址</div><div>{order.shipping_address || "-"}</div>
          <div className="sales-print-label">开票地址</div><div>{order.billing_address || "-"}</div>
        </div>
      </section>

      <section className="sales-print-section">
        <h2><span>02</span> 商务与交付信息</h2>
        <div className="sales-print-meta">
          <div><span>客户订单号</span><strong>{order.customer_po_no || "-"}</strong></div>
          <div><span>关联报价</span><strong>{order.quotation_no || (order.quotation_id ? `#${order.quotation_id}` : "-")}</strong></div>
          <div><span>结算币种</span><strong>{order.currency || "CNY"}</strong></div>
          <div><span>贸易条款</span><strong>{order.incoterms || "-"}</strong></div>
          <div><span>付款条件</span><strong>{order.payment_terms || "-"}</strong></div>
          <div><span>付款到期</span><strong>{date(order.due_date)}</strong></div>
          <div><span>下单日期</span><strong>{date(order.order_date)}</strong></div>
          <div><span>预计交付</span><strong>{date(order.delivery_date)}</strong></div>
        </div>
      </section>

      <section className="sales-print-section">
        <h2><span>03</span> 产品明细与价款</h2>
        <table className="sales-print-table">
          <thead><tr><th>#</th><th>产品名称 / 规格</th><th>单位</th><th className="number">数量</th><th className="number">含税单价</th><th className="number">折扣</th><th className="number">税率</th><th className="number">价税合计</th><th>备注</th></tr></thead>
          <tbody>{order.items.map((item, index) => (
            <tr key={item.id}>
              <td>{index + 1}</td><td><strong>{item.product_name || "-"}</strong><small>{item.product_id ? `产品 #${item.product_id}` : ""}</small></td>
              <td>{item.unit || "-"}</td><td className="number">{Number(item.quantity || 0).toLocaleString("zh-CN")}</td>
              <td className="number">{amount(item.unit_price, order.currency, 6)}</td><td className="number">{item.discount_rate == null ? "-" : `${item.discount_rate}%`}</td>
              <td className="number">{item.tax_rate == null ? "-" : `${item.tax_rate}%`}</td><td className="number"><strong>{amount(item.total_price, order.currency)}</strong></td>
              <td>{item.notes || "-"}</td>
            </tr>
          ))}</tbody>
          <tfoot><tr><td colSpan={3}>合计</td><td className="number"><strong>{quantity.toLocaleString("zh-CN")}</strong></td><td colSpan={3} /><td className="number"><strong>{amount(order.total_amount, order.currency)}</strong></td><td /></tr></tfoot>
        </table>
        <div className="sales-print-totals">
          <div><span>未税金额</span><strong>{amount(untaxed, order.currency)}</strong></div>
          <div><span>税额</span><strong>{amount(tax, order.currency)}</strong></div>
          <div className="grand"><span>价税合计</span><strong>{amount(order.total_amount, order.currency)}</strong></div>
        </div>
      </section>

      <section className="sales-print-section sales-print-terms">
        <h2><span>04</span> 订单约定</h2>
        <ol>
          <li>产品、数量、价格及交期以本订单及双方书面确认内容为准。</li>
          <li>甲方应按约定完成收货验收；外观、数量异常应在签收后及时书面反馈。</li>
          <li>付款、开票、运输及质保事项按本订单、关联销售合同或双方补充协议执行。</li>
        </ol>
        {order.notes && <p><strong>订单备注：</strong>{order.notes}</p>}
      </section>

      <section className="sales-print-signatures">
        <div><h3>甲方（采购方）</h3><strong>{order.customer_name || `客户 #${order.customer_id}`}</strong><p>授权代表：________________</p><p>签章：____________________</p><p>日期：____年__月__日</p></div>
        <div><h3>乙方（销售方）</h3><strong>{SELLER_NAME}</strong><p>授权代表：________________</p><p>签章：____________________</p><p>日期：____年__月__日</p></div>
      </section>
      <footer className="sales-print-footer"><span>{order.order_no || `SO-${order.id}`}</span><span>销售订单 · ERP 系统生成</span><span>第 1 页</span></footer>
    </section></SalesPrintPortal>
  );
}

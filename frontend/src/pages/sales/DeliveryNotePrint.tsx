import type { DeliveryNote } from "../../types";
import { SalesPrintPortal } from "./SalesPrintPortal";
import "./salesDocumentPrint.css";

const SELLER_NAME = "深圳天允电子有限公司";
const STATUS: Record<string, string> = {
  pending: "待发货",
  shipped: "已发货",
  delivered: "已签收",
  returned: "已退回",
  cancelled: "已取消",
};

function date(value: string | null | undefined) {
  return value ? value.slice(0, 10) : "-";
}

export function DeliveryNotePrint({ note }: { note: DeliveryNote }) {
  const quantity = note.items.reduce((sum, item) => sum + Number(item.quantity || 0), 0);

  return (
    <SalesPrintPortal><section className="sales-document-print" data-testid="delivery-note-print" aria-label="销售送货单打印单据">
      {note.status === "pending" && <div className="sales-print-watermark">待发货 · 请勿签收</div>}
      {["returned", "cancelled"].includes(note.status) && <div className="sales-print-watermark sales-print-watermark-danger">{STATUS[note.status]}</div>}

      <header className="sales-print-header">
        <div className="sales-print-brand"><strong>{SELLER_NAME}</strong><span>TIANYUN ELECTRONICS · LOGISTICS</span></div>
        <div className="sales-print-title"><h1>销售送货单</h1><span>DELIVERY NOTE</span></div>
        <div className="sales-print-control">
          <span>送货单号</span><strong>{note.delivery_no || `DN-${note.id}`}</strong>
          <span>单据状态</span><strong>{STATUS[note.status] || note.status}</strong>
          <span>制单日期</span><strong>{date(note.created_at)}</strong>
        </div>
      </header>

      <section className="sales-print-section">
        <h2><span>01</span> 收发货信息</h2>
        <div className="sales-print-party-grid">
          <div className="sales-print-label">收货单位</div><div className="sales-print-party-name">{note.customer_name || `客户 #${note.customer_id}`}</div>
          <div className="sales-print-label">发货单位</div><div className="sales-print-party-name">{SELLER_NAME}</div>
          <div className="sales-print-label">关联订单</div><div>{note.sales_order_no || `订单 #${note.sales_order_id}`}</div>
          <div className="sales-print-label">贸易条款</div><div>{note.incoterms || "-"}</div>
        </div>
      </section>

      <section className="sales-print-section">
        <h2><span>02</span> 运输与签收信息</h2>
        <div className="sales-print-meta">
          <div><span>发货日期</span><strong>{date(note.delivery_date)}</strong></div>
          <div><span>运输方式</span><strong>{note.shipping_method || "-"}</strong></div>
          <div><span>运单号码</span><strong>{note.tracking_number || "-"}</strong></div>
          <div><span>签收日期</span><strong>{date(note.received_date)}</strong></div>
        </div>
      </section>

      <section className="sales-print-section">
        <h2><span>03</span> 交付明细</h2>
        <table className="sales-print-table delivery-items">
          <thead><tr><th>#</th><th>产品名称 / 规格</th><th>单位</th><th className="number">本次交付数量</th><th>备注</th></tr></thead>
          <tbody>{note.items.map((item, index) => (
            <tr key={item.id}>
              <td>{index + 1}</td>
              <td><strong>{item.product_name || "-"}</strong><small>{item.product_id ? `产品 #${item.product_id}` : ""}</small></td>
              <td>{item.unit || "-"}</td>
              <td className="number">{Number(item.quantity || 0).toLocaleString("zh-CN")}</td>
              <td>{item.notes || "-"}</td>
            </tr>
          ))}</tbody>
          <tfoot><tr><td colSpan={3}>合计</td><td className="number"><strong>{quantity.toLocaleString("zh-CN")}</strong></td><td /></tr></tfoot>
        </table>
      </section>

      <section className="sales-print-section sales-print-terms">
        <h2><span>04</span> 验收说明</h2>
        <ol>
          <li>收货方请按本单核对产品名称、包装和数量，确认无误后签收。</li>
          <li>如有外观、包装或数量异常，请在签收时注明并及时联系发货方。</li>
          <li>本送货单仅作交付与签收凭证，结算事项以销售订单、合同及发票为准。</li>
        </ol>
        {note.notes && <p><strong>送货备注：</strong>{note.notes}</p>}
      </section>

      <section className="sales-print-signatures">
        <div><h3>收货方确认</h3><strong>{note.customer_name || `客户 #${note.customer_id}`}</strong><p>收货人：________________</p><p>签章：__________________</p><p>日期：____年__月__日</p></div>
        <div><h3>发货方确认</h3><strong>{SELLER_NAME}</strong><p>发货人：________________</p><p>复核：__________________</p><p>日期：____年__月__日</p></div>
      </section>
      <footer className="sales-print-footer"><span>{note.delivery_no || `DN-${note.id}`}</span><span>销售送货单 · ERP 系统生成</span><span>第 1 页</span></footer>
    </section></SalesPrintPortal>
  );
}

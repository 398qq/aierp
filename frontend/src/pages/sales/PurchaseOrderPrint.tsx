import type { PurchaseOrder, PurchaseOrderItem } from "../../types";
import "./purchaseOrderPrint.css";

type PrintablePurchaseOrder = PurchaseOrder & { items: PurchaseOrderItem[] };

const currencySymbol: Record<string, string> = { CNY: "¥", USD: "$", EUR: "€", HKD: "HK$" };

function amount(value: number | null | undefined, currency = "CNY", maximumFractionDigits = 2) {
  const symbol = currencySymbol[currency] || `${currency} `;
  return `${symbol}${Number(value || 0).toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits,
  })}`;
}

function date(value: string | null | undefined) {
  return value ? value.slice(0, 10) : "-";
}

export function PurchaseOrderPrint({ po }: { po: PrintablePurchaseOrder }) {
  const quantity = po.items.reduce((sum, item) => sum + Number(item.quantity || 0), 0);

  return (
    <section className="purchase-order-print" data-testid="purchase-order-print" aria-label="采购订单打印单据">
      <header className="po-print-header">
        <div className="po-print-document-type">PURCHASE ORDER</div>
        <h1>采购订单</h1>
        <div className="po-print-version">模板 {po.contract_terms_version || "v3.4"}</div>
      </header>

      <div className="po-print-meta">
        <div><span>订单号</span><strong>{po.order_no || `PO-${po.id}`}</strong></div>
        <div><span>创建日期</span><strong>{date(po.created_at)}</strong></div>
        <div><span>供应商</span><strong>{po.supplier_name || "-"}</strong></div>
        <div><span>联系人</span><strong>{po.supplier_contact || "-"}</strong></div>
        <div><span>付款方式</span><strong>{po.payment_terms || "-"}</strong></div>
        <div><span>预计交期</span><strong>{date(po.expected_date)}</strong></div>
        <div><span>关联销售订单</span><strong>{po.sales_order_no || "-"}</strong></div>
        <div><span>关联客户</span><strong>{po.customer_name || "-"}</strong></div>
        <div className="po-print-meta-wide"><span>交货地址</span><strong>{po.delivery_address || "-"}</strong></div>
      </div>

      <table className="po-print-table">
        <thead>
          <tr>
            <th>#</th><th>供应商型号 / 自有 SKU</th><th>品名 / 品牌</th><th>封装</th>
            <th className="po-print-number">数量</th><th>最小包装</th><th>生产批次</th>
            <th className="po-print-number">含税单价</th><th className="po-print-number">金额</th><th>备注</th>
          </tr>
        </thead>
        <tbody>
          {po.items.map((item, index) => (
            <tr key={item.id}>
              <td>{index + 1}</td>
              <td><strong>{item.supplier_mpn || "-"}</strong><small>{item.product_sku || "-"}</small></td>
              <td>{item.product_name || "-"}<small>{item.brand_name || "-"}</small></td>
              <td>{item.package_type || "-"}</td>
              <td className="po-print-number">{Number(item.quantity || 0).toLocaleString("zh-CN")} {item.unit || "pcs"}</td>
              <td>{item.min_pack_qty ? `${Number(item.min_pack_qty).toLocaleString("zh-CN")}/${item.min_pack_unit || "包"}` : "-"}</td>
              <td><strong>{item.date_code_requirement || "不限"}</strong></td>
              <td className="po-print-number">{amount(item.unit_price, po.currency, 6)}</td>
              <td className="po-print-number"><strong>{amount(item.amount, po.currency)}</strong></td>
              <td>{item.notes || item.customer_name || "-"}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <td colSpan={4}>合计</td>
            <td className="po-print-number"><strong>{quantity.toLocaleString("zh-CN")} pcs</strong></td>
            <td colSpan={3} />
            <td className="po-print-number"><strong>{amount(po.total_amount, po.currency)}</strong></td>
            <td />
          </tr>
        </tfoot>
      </table>

      <div className="po-print-totals">
        <div><span>未税金额</span><strong>{amount(po.subtotal, po.currency)}</strong></div>
        <div><span>税率</span><strong>{Number(po.tax_rate || 0)}%</strong></div>
        <div><span>税额</span><strong>{amount(po.tax_amount, po.currency)}</strong></div>
        <div className="po-print-grand-total"><span>价税合计</span><strong>{amount(po.total_amount, po.currency)}</strong></div>
      </div>

      <div className="po-print-notes">
        <div><span>订单备注：</span>{po.notes || "无"}</div>
        <div><span>交付要求：</span>{po.allow_partial_delivery ? "允许分批交货" : "不允许分批交货"}；生产批次须按明细逐项验收。</div>
        <div><span>合同效力：</span>本采购订单适用采购合同条款 {po.contract_terms_version || "v3.4"}；供应商确认本 PO 即视为接受随单条款。</div>
      </div>

      <footer className="po-print-footer">
        <div>采购方签章：____________________</div>
        <div>供应方确认：____________________</div>
        <div>确认日期：____________________</div>
      </footer>
    </section>
  );
}

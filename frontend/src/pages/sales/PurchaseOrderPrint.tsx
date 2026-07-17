import type { PurchaseOrder, PurchaseOrderItem } from "../../types";
import { PurchaseContractTerms } from "./PurchaseContractTerms";
import "./purchaseOrderPrint.css";

type PrintablePurchaseOrder = PurchaseOrder & { items: PurchaseOrderItem[] };

const PURCHASER_NAME = "深圳天允电子有限公司";
const currencySymbol: Record<string, string> = { CNY: "¥", USD: "$", EUR: "€", HKD: "HK$" };
const statusLabel: Record<string, string> = {
  draft: "草稿",
  approved: "已审批",
  ordered: "已下单",
  partially_received: "部分收货",
  received: "已收货",
  cancelled: "已取消",
};

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

function cnyUppercase(value: number | null | undefined) {
  const number = Math.round(Number(value || 0) * 100);
  if (!Number.isFinite(number) || number === 0) return "人民币零元整";
  const digits = ["零", "壹", "贰", "叁", "肆", "伍", "陆", "柒", "捌", "玖"];
  const units = ["分", "角", "元", "拾", "佰", "仟", "万", "拾", "佰", "仟", "亿", "拾", "佰", "仟", "万"];
  let result = "";
  let zeroPending = false;
  String(number).split("").reverse().forEach((raw, index) => {
    const digit = Number(raw);
    const unit = units[index] || "";
    if (digit === 0) {
      if ([2, 6, 10, 14].includes(index)) {
        if (!result.startsWith(unit)) result = unit + result;
        zeroPending = false;
      } else if (result && !result.startsWith("零")) {
        zeroPending = true;
      }
      return;
    }
    result = `${digits[digit]}${unit}${zeroPending ? "零" : ""}${result}`;
    zeroPending = false;
  });
  result = result.replace(/零+/g, "零").replace(/零(万|亿|元)/g, "$1").replace(/亿万/g, "亿");
  if (!result.includes("角") && !result.includes("分")) result += "整";
  return `人民币${result}`;
}

export function PurchaseOrderPrint({ po, includeCustomerReferences = false }: { po: PrintablePurchaseOrder; includeCustomerReferences?: boolean }) {
  const quantity = po.items.reduce((sum, item) => sum + Number(item.quantity || 0), 0);

  return (
    <section className="purchase-order-print" data-testid="purchase-order-print" aria-label="采购订单打印单据">
      <main className="po-print-contract-body">
        {po.status === "draft" && <div className="po-print-watermark">草稿 · 非正式合同</div>}
        {po.status === "cancelled" && <div className="po-print-watermark po-print-watermark-danger">已取消</div>}

        <header className="po-print-header">
          <div className="po-print-brand">
            <strong>{PURCHASER_NAME}</strong>
            <span>TIANYUN ELECTRONICS · PROCUREMENT</span>
          </div>
          <div className="po-print-title">
            <h1>采购合同</h1>
            <div>PURCHASE ORDER / CONTRACT</div>
          </div>
          <div className="po-print-control">
            <span>合同编号</span><strong>{po.order_no || `PO-${po.id}`}</strong>
            <span>状态</span><strong>{statusLabel[po.status] || po.status}</strong>
            <span>条款版本</span><strong>{po.contract_terms_version || "v3.4"}</strong>
          </div>
        </header>

        <section className="po-print-section po-print-parties">
          <h2><span>01</span> 合同主体</h2>
          <div className="po-print-party-grid">
            <div className="po-print-party-role">甲方 / 采购方</div>
            <div className="po-print-party-name">{PURCHASER_NAME}</div>
            <div className="po-print-party-role">乙方 / 供应方</div>
            <div className="po-print-party-name">{po.supplier_name || "-"}</div>
            <div className="po-print-party-label">交货地址</div>
            <div>{po.delivery_address || "-"}</div>
            <div className="po-print-party-label">业务联系人</div>
            <div>{po.supplier_contact || "-"}</div>
          </div>
        </section>

        <section className="po-print-section">
          <h2><span>02</span> 商务与交付条件</h2>
          <div className="po-print-meta">
            <div><span>签订日期</span><strong>{date(po.created_at)}</strong></div>
            <div><span>预计交期</span><strong>{date(po.expected_date)}</strong></div>
            <div><span>结算币种</span><strong>{po.currency || "CNY"}</strong></div>
            <div><span>贸易术语</span><strong>{po.incoterms || "DDP"}</strong></div>
            <div><span>付款方式</span><strong>{po.payment_terms || "-"}</strong></div>
            <div><span>增值税率</span><strong>{Number(po.tax_rate || 0)}%</strong></div>
            <div><span>分批交货</span><strong>{po.allow_partial_delivery ? "允许" : "不允许"}</strong></div>
            <div><span>供应商确认</span><strong>{po.supplier_confirmation_status === "confirmed" ? "已书面确认" : "待确认"}</strong></div>
            {includeCustomerReferences && <>
              <div className="po-print-meta-half"><span>内部关联 SO</span><strong>{po.sales_order_no || "-"}</strong></div>
              <div className="po-print-meta-half"><span>内部关联客户</span><strong>{po.customer_name || "-"}</strong></div>
            </>}
          </div>
        </section>

        <section className="po-print-section">
          <h2><span>03</span> 采购标的与价款</h2>
          <table className="po-print-table">
        <thead>
          <tr>
            <th>#</th><th>供应商型号 / 自有 SKU</th><th>品名 / 品牌</th><th>封装</th>
            <th className="po-print-number">数量</th><th>最小包装</th><th>生产批次</th>
            <th className="po-print-number">含税单价</th><th className="po-print-number">金额</th>
            {includeCustomerReferences && <th>内部关联 / 备注</th>}
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
              {includeCustomerReferences && <td>{item.notes || item.customer_name || "-"}</td>}
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <td colSpan={4}>合计</td>
            <td className="po-print-number"><strong>{quantity.toLocaleString("zh-CN")} pcs</strong></td>
            <td colSpan={3} />
            <td className="po-print-number"><strong>{amount(po.total_amount, po.currency)}</strong></td>
            {includeCustomerReferences && <td />}
          </tr>
        </tfoot>
          </table>

          <div className="po-print-settlement">
            <div className="po-print-uppercase"><span>价税合计（大写）</span><strong>{po.currency === "CNY" ? cnyUppercase(po.total_amount) : `${po.currency} ${Number(po.total_amount || 0).toFixed(2)}`}</strong></div>
            <div className="po-print-totals">
              <div><span>未税金额</span><strong>{amount(po.subtotal, po.currency)}</strong></div>
              <div><span>税额</span><strong>{amount(po.tax_amount, po.currency)}</strong></div>
              <div className="po-print-grand-total"><span>价税合计</span><strong>{amount(po.total_amount, po.currency)}</strong></div>
            </div>
          </div>
        </section>

        <section className="po-print-section po-print-execution">
          <h2><span>04</span> 履约与验收要求</h2>
          <div className="po-print-execution-grid">
            <div><strong>批次与正品</strong><span>逐行满足生产批次要求；须为原厂正品、全新、未翻新、未打磨、未改字。</span></div>
            <div><strong>包装与标识</strong><span>按原厂 ESD/MSL 标准包装，外箱标注 PO、MPN/SKU、品牌、封装、批次和数量。</span></div>
            <div><strong>到货验收</strong><span>签收后进行数量、包装、外观和文件检查，并保留 30 日上机验证权利。</span></div>
            <div><strong>发票与付款</strong><span>验收、对账及合法有效发票三项齐备后，按本合同约定付款。</span></div>
          </div>
          {includeCustomerReferences && po.notes && <div className="po-print-internal-note"><strong>内部备注：</strong>{po.notes}</div>}
          <p className="po-print-legal-notice">本合同正文与后附《采购合同条款 {po.contract_terms_version || "v3.4"}》共同构成完整合同。乙方签章、书面确认 PO 或实际交付货物，均视为已阅读并接受全部约定。</p>
        </section>

        <section className="po-print-signatures">
          <div>
            <h3>甲方（采购方）</h3>
            <strong>{PURCHASER_NAME}</strong>
            <p>授权代表：____________________</p><p>签章：________________________</p><p>日期：______年____月____日</p>
          </div>
          <div>
            <h3>乙方（供应方）</h3>
            <strong>{po.supplier_name || "-"}</strong>
            <p>授权代表：____________________</p><p>签章：________________________</p><p>日期：______年____月____日</p>
          </div>
        </section>
        <footer className="po-print-page-footer"><span>{po.order_no || `PO-${po.id}`}</span><span>采购合同正文 · ERP 系统生成</span><span>合同正文</span></footer>
      </main>
      <PurchaseContractTerms orderNo={po.order_no || `PO-${po.id}`} purchaserName={PURCHASER_NAME} supplierName={po.supplier_name || "-"} />
    </section>
  );
}

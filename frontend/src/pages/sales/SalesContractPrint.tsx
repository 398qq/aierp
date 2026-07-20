import type { Contract, SalesOrder } from "../../types";
import "./salesDocumentPrint.css";

const SELLER_NAME = "深圳天允电子有限公司";
const STATUS: Record<string, string> = { draft: "草稿", signed: "已签署", active: "履行中", expired: "已到期", terminated: "已终止" };

function date(value: string | null | undefined) { return value ? value.slice(0, 10) : "-"; }
function money(value: number | null | undefined, currency = "CNY") {
  const symbols: Record<string, string> = { CNY: "¥", USD: "$", EUR: "€", HKD: "HK$" };
  return `${symbols[currency] || `${currency} `}${Number(value || 0).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function SalesContractPrint({ contract, order, customerName }: { contract: Contract; order: SalesOrder | null; customerName: string }) {
  const buyer = customerName || order?.customer_name || `客户 #${contract.customer_id}`;
  return (
    <section className="sales-document-print" data-testid="sales-contract-print" aria-label="销售合同打印单据">
      {contract.status === "draft" && <div className="sales-print-watermark">草稿 · 非正式合同</div>}
      {contract.status === "terminated" && <div className="sales-print-watermark sales-print-watermark-danger">已终止</div>}
      <header className="sales-print-header">
        <div className="sales-print-brand"><strong>{SELLER_NAME}</strong><span>TIANYUN ELECTRONICS · CONTRACT</span></div>
        <div className="sales-print-title"><h1>销售合同</h1><span>SALES CONTRACT</span></div>
        <div className="sales-print-control"><span>合同编号</span><strong>{contract.contract_no || `CT-${contract.id}`}</strong><span>合同状态</span><strong>{STATUS[contract.status] || contract.status}</strong><span>签署日期</span><strong>{date(contract.signed_date)}</strong></div>
      </header>

      <section className="sales-print-section"><h2><span>01</span> 合同主体</h2><div className="sales-print-party-grid">
        <div className="sales-print-label">甲方 / 采购方</div><div className="sales-print-party-name">{buyer}</div><div className="sales-print-label">乙方 / 销售方</div><div className="sales-print-party-name">{SELLER_NAME}</div>
        <div className="sales-print-label">合同名称</div><div>{contract.title}</div><div className="sales-print-label">交货地址</div><div>{contract.delivery_address || order?.shipping_address || "-"}</div>
      </div></section>

      <section className="sales-print-section"><h2><span>02</span> 合同信息</h2><div className="sales-print-meta">
        <div><span>合同金额</span><strong>{money(contract.amount, contract.currency)}</strong></div><div><span>结算币种</span><strong>{contract.currency || "CNY"}</strong></div>
        <div><span>签署日期</span><strong>{date(contract.signed_date)}</strong></div><div><span>有效期至</span><strong>{date(contract.expire_date)}</strong></div>
        <div><span>关联订单</span><strong>{order?.order_no || (contract.sales_order_id ? `#${contract.sales_order_id}` : "-")}</strong></div><div><span>发票类型</span><strong>{contract.invoice_type || "-"}</strong></div>
        <div className="wide"><span>合同备注</span><strong>{contract.notes || "-"}</strong></div>
      </div></section>

      <section className="sales-print-section"><h2><span>03</span> 合同标的</h2>
        {order?.items.length ? <table className="sales-print-table contract-items"><thead><tr><th>#</th><th>产品名称 / 规格</th><th>单位</th><th className="number">数量</th><th className="number">含税单价</th><th className="number">税率</th><th className="number">价税合计</th></tr></thead><tbody>
          {order.items.map((item, index) => <tr key={item.id}><td>{index + 1}</td><td><strong>{item.product_name || "-"}</strong></td><td>{item.unit || "-"}</td><td className="number">{Number(item.quantity || 0).toLocaleString("zh-CN")}</td><td className="number">{money(item.unit_price, contract.currency)}</td><td className="number">{item.tax_rate == null ? "-" : `${item.tax_rate}%`}</td><td className="number"><strong>{money(item.total_price, contract.currency)}</strong></td></tr>)}
        </tbody><tfoot><tr><td colSpan={3}>合计</td><td className="number"><strong>{order.items.reduce((sum, item) => sum + Number(item.quantity || 0), 0).toLocaleString("zh-CN")}</strong></td><td colSpan={2} /><td className="number"><strong>{money(contract.amount, contract.currency)}</strong></td></tr></tfoot></table> : <div className="sales-print-empty">本合同未关联销售订单，合同标的以双方确认的附件、报价单或补充协议为准。</div>}
      </section>

      <section className="sales-print-section"><h2><span>04</span> 商务条款</h2><div className="sales-print-clauses">
        <article><h3>付款条款</h3><p>{contract.payment_terms || order?.payment_terms || "按双方书面约定执行。"}</p></article>
        <article><h3>交付条款</h3><p>{contract.delivery_terms || "乙方按约定时间、地点及方式完成交付。"}</p></article>
        <article><h3>验收条款</h3><p>{contract.acceptance_terms || "甲方应在收货后及时完成数量、外观及质量验收。"}</p></article>
        <article><h3>质保与售后</h3><p>{contract.warranty_terms || "产品质保及售后责任按原厂政策与双方约定执行。"}</p></article>
        <article className="wide"><h3>违约责任与争议解决</h3><p>{contract.dispute_terms || "任何一方违约应承担相应责任；争议应先友好协商，协商不成依法解决。"}</p></article>
      </div></section>

      <section className="sales-print-signatures"><div><h3>甲方（采购方）</h3><strong>{buyer}</strong><p>授权代表：________________</p><p>签章：____________________</p><p>日期：____年__月__日</p></div><div><h3>乙方（销售方）</h3><strong>{SELLER_NAME}</strong><p>授权代表：________________</p><p>签章：____________________</p><p>日期：____年__月__日</p></div></section>
      <footer className="sales-print-footer"><span>{contract.contract_no || `CT-${contract.id}`}</span><span>销售合同 · ERP 系统生成</span><span>合同正文</span></footer>
    </section>
  );
}

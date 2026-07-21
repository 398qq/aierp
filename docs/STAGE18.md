# Stage 18 — Production Batch Management

**Last Updated**: 2026-07-21
**Commits**: f8685e6e (P0) · a52d3238 (P1) · 55b1d17a (P2) · fc12f982 (P3) · af70e00b (P4) · e06b5280 (P5)
**Tests**: 61 / 61 ✅ (6 + 10 + 8 + 6 + 11 + 20)
**Lint**: ruff ✅ · mypy ✅ · frontend typecheck ✅

---

## Why this exists

A `batch_no` in a real ERP isn't a row — it's a *lineage* spanning warehouses, suppliers, customers, expiry dates, and recall history. The old code only had `InventoryBatchORM` (a row) and `deduct_for_delivery` (a quantity subtracter). No way to answer:

- *Where did this batch go?* (recall / warranty / cross-warehouse audit)
- *Which customers are affected if we recall this batch?*
- *When does this batch expire — and who needs to know?*
- *Can we move 50 pcs to the Shanghai warehouse?*
- *Two operators accidentally created the same batch — can we merge them?*

Stage 18 answers all five.

---

## Architecture

```
   ┌──────────────┐
   │ Supplier PO  │
   └──────┬───────┘
          │ receive
          ▼
   ┌──────────────────┐         InventoryTransaction
   │ InventoryBatchORM│ ──FK──▶ (product_id, warehouse_id,
   │   - batch_no      │         reference_id, **batch_id**, qty)
   │   - warehouse_id  │
   │   - quantity      │         ▲       ▲
   │   - expiry_date   │         │       │
   │   - status        │         │       │ (type='transfer'|'adjust'|
   │   - batch_id FK ──│─────────┘       │  'stock_in'|'stock_out')
   └──────────────────┘                 │
          ▲                              │
          │ (find-or-create by            │ (every stock movement
          │  product+warehouse+batch_no)  │  carries batch_id)
          │                              │
   ┌──────┴──────┐  transfer   ┌─────────┴──────────┐
   │ Warehouse A │ ◀──────────▶ │ Warehouse B       │
   └─────────────┘             └────────────────────┘
```

**The pivotal change**: every `InventoryTransaction` now carries `batch_id`. One column, one index, one FK — and every downstream query (traceability, expiry, recall) suddenly becomes *batch-precise* instead of *product-warehouse-precise*.

---

## P0 — 批次追溯 (Batch Traceability) · `f8685e6e`

**Problem**: Given a `batch_id`, who did this batch go to? And where did it come from?

**Solution**: `BatchTraceabilityService.get_traceability(db, batch_id)` returns:

```python
{
  "batch":      {"id": 1, "batch_no": "B2026-001", "expiry_date": ...},
  "upstream":   {"supplier": {...}, "purchase_orders": [...], "stock_in_records": [...]},
  "downstream": {"customers": [...], "deliveries": [...], "total_quantity_consumed": 70},
}
```

- **Upstream**: `InventoryTransaction` WHERE `batch_id=X AND type='stock_in'` + supplier lookup
- **Downstream**: `stock_out` txns joined to `DeliveryNote` → `SalesOrder` → `Customer` (distinct)

**API**: `GET /api/v1/inventory/batches/{batch_id}/traceability`
**Frontend**: `/inventory/batches/:id/traceability` — dual-column layout (upstream | downstream)
**Migration**: `0018_inventory_transaction_batch_id` (FK + index)

---

## P1 — 有效期预警 (Expiry Alert) · `a52d3238`

**Problem**: 30 days before a batch expires, someone should know.

**Solution**: `ExpiryAlertService.scan()` 4-bucket classification:
- `expired` (days ≤ 0) — critical
- `7d` (1–7 days) — high
- `30d` (8–30 days) — medium
- `90d` (31–90 days) — low

Calendar-day diff (not `timedelta.days` which truncates to −∞), warehouse filter, batch_no, quantity, unit_cost surfaced. Excludes `status in (consumed, recalled) AND qty <= 0`.

**APIs**:
- `GET /inventory/batches/expiring?buckets=expired,7d&warehouse_id=X`
- `GET /inventory/batches/expiring/summary`

**Frontend**: `/inventory/expiring` — 4 tabbed tables, severity-colored stat cards

---

## P2 — 召回流程 (Recall) · `55b1d17a`

**Problem**: Supplier issues a recall. We need to (1) know which customers are affected *before* pulling the trigger, (2) freeze the batch, (3) audit.

**Solution**: `BatchRecallService`:
- `get_impact(db, batch_id)` — reuses traceability, returns affected customers + deliveries
- `recall_batch(db, batch_id, reason, actor)` — sets `status=recalled`, `locked_quantity >= remaining` (freeze), rejects double-recall (idempotent), empty reason, non-`available` status

**APIs**:
- `GET /inventory/batches/{batch_id}/recall-impact` — preview
- `POST /inventory/batches/{batch_id}/recall` body=`{reason, actor?}`

**Frontend**: `/inventory/batches/:id/recall` — 2-step wizard (impact preview → reason form)

---

## P3 — 有效期定时 job (Expiry Scheduled Job) · `fc12f982`

**Problem**: P1 gives you the data. P3 makes sure someone actually looks at it.

**Solution**: `_check_batch_expiry` in `app/jobs/scheduler.py`, registered as `interval 24h`. Mirrors `_check_contract_expiry` pattern:
- Calls `expiry_alert_service.scan(buckets=["expired", "7d"])`
- One `NotificationService.create_notification()` per affected batch
- Only `expired` + `7d` (not `30d`/`90d` — those are weekly-bucket candidates for a separate job)
- Admin user (`user_id=1`) for now; TODO: per-warehouse routing

**Scheduler total**: 12 jobs.

---

## P4 — 批次调拨 (Batch Transfer) · `af70e00b`

**Problem**: Move 50 pcs from Shenzhen warehouse to Shanghai warehouse, preserving the batch lineage.

**Solution**: `BatchTransferService.transfer_batch()`:
- Decrement `src.batch.quantity` (mark `consumed` if 0)
- Find-or-create `dst` batch (same `product_id` + `batch_no`, new `warehouse_id`); inherit `unit_cost` / `expiry_date` / `supplier_id` / `msl_level` / `cert`
- Write **paired** `InventoryTransaction` rows: `src stock_out` + `dst stock_in`, both `type='transfer'`, both `batch_id` (src.id and dst.id respectively)
- Validations: qty > 0, dst exists, dst != src, `available` (= qty − locked) sufficient, `status='available'`

**API**: `POST /inventory/batches/{batch_id}/transfer` body=`{dst_warehouse_id, quantity, reason, actor?}`

---

## P5 — 批次间调拨 merge/split · `e06b5280`

**Problem**: (1) Two batches accidentally created — merge them. (2) Need to split a batch for different customers / packaging.

### `BatchMergeService.merge_batches()`

- All batches must share `product_id` + `warehouse_id` (batch_nos **may differ** — unique constraint already prevents same-key duplicates)
- Survivor = lowest id (oldest); others marked `status=consumed, qty=0` (keep ids for traceability history)
- Survivor's `quantity = sum`, `unit_cost = weighted average`, `expiry_date = earliest`
- **20 tests** including 3-batch weighted-cost (10×5 + 20×10 + 30×15 = 700 → 11.67) and different-batch-no merge

### `BatchSplitService.split_batch()`

- `0 < quantity < src.quantity` (equal = transfer, not split)
- New `batch_no` auto-generated as `{src}-S1` (collision-checked, increments to `-S2`, `-S3`...)
- New batch inherits all quality attrs (cert, msl, expiry, supplier)
- Source `quantity -= qty`; new batch `quantity = qty`
- **12 tests** including auto-number collision, explicit batch_no, src-consumed-at-zero

**APIs**:
- `POST /inventory/batches/merge` body=`{batch_ids: [≥2], reason, actor?}`
- `POST /inventory/batches/{batch_id}/split` body=`{quantity, new_batch_no?, reason, actor?}`

---

## Test statistics

| Module | Tests | Coverage focus |
|---|---|---|
| `test_batch_traceability.py` | 6 | core / upstream / downstream / multi-customer / empty / missing |
| `test_expiry_alert.py` | 10 | empty / expired / 7d / 30d boundary / status filter / warehouse / null expiry / invalid bucket / summary |
| `test_batch_recall.py` | 8 | impact missing/with-customers / status + freeze / no-double-freeze / idempotency / empty reason / missing / multi-customer |
| `test_batch_expiry_job.py` | 6 | empty / expired / 7d / skip 30d+90d / mixed / consumed |
| `test_batch_transfer.py` | 11 | new-dst / append / paired-txns / consumed-at-zero / qty≤0 / empty reason / same-wh / unknown dst / unknown batch / insufficient / non-available |
| `test_batch_merge_split.py` | 20 | merge 9 + split 11 (consolidate / audit-txns / weighted-cost / diff-batch-nos / auto-number / collision / explicit-no / src-consumed-at-zero / etc.) |
| **Total** | **61** | ✅ |

---

## Cumulative git history (Stage 18 + misc)

```
e06b5280  feat(batch): 批次间调拨 - merge/split (P5)
af70e00b  feat(batch): 批次调拨 - 同/跨仓库 (P4)
fc12f982  feat(batch): 有效期定时 job 通知 (P3)
55b1d17a  feat(batch): 召回流程 (P2)
a52d3238  feat(batch): 有效期预警 (P1)
f8685e6e  feat(batch): 批次追溯 (P0)
96d27f39  chore: 阶段 0 杂项修复
373c23ee  feat(bot): Telegram code-expert bot 集成
937284ea  fix: 销售单与报价单列表拆分为单号和客户名称独立列
```

---

## Known limitations & future work

| Item | Severity | Notes |
|---|---|---|
| `_check_batch_expiry` hardcodes `user_id=1` (admin) | 🟡 Medium | Should route to warehouse managers; need a `user_warehouses` mapping table |
| 30d / 90d bucket notifications not wired to scheduler | 🟢 Low | P3 only fires on `expired` + `7d`; add a weekly job for the other two |
| Recall notifications not auto-sent | 🟡 Medium | P2 returns the impact; the API caller must call `notification_service.create_notification` per affected customer |
| Transfer / merge / split frontend buttons | 🟢 Low | APIs exist; InventoryBatches page needs action buttons |
| Batch `product_id + batch_no` uniqueness across warehouses is a *logical* invariant; model currently allows same-key across warehouses (correct) but `merge_batches` rejects the impossible case explicitly | 🟢 Trivial | Documented in service docstring |
| `InventoryTransaction.reference_id` for transfer / merge / split is `None` | 🟢 Low | Currently linked via `notes` + `reference_type`; could add a `Transfer` / `Merge` / `Split` record table for full audit |

---

## API quick-reference (all under `/api/v1`)

```
# P0 追溯
GET    /inventory/batches/{batch_id}/traceability

# P1 预警
GET    /inventory/batches/expiring?buckets=expired,7d,30d,90d&warehouse_id=X
GET    /inventory/batches/expiring/summary?warehouse_id=X

# P2 召回
GET    /inventory/batches/{batch_id}/recall-impact
POST   /inventory/batches/{batch_id}/recall      {reason, actor?}

# P4 调拨
POST   /inventory/batches/{batch_id}/transfer    {dst_warehouse_id, quantity, reason, actor?}

# P5 merge / split
POST   /inventory/batches/merge                  {batch_ids: [≥2], reason, actor?}
POST   /inventory/batches/{batch_id}/split       {quantity, new_batch_no?, reason, actor?}
```

## Frontend pages

- `/inventory/expiring` — 4-bucket expiry dashboard
- `/inventory/batches/:id/traceability` — upstream / downstream timeline
- `/inventory/batches/:id/recall` — 2-step recall wizard

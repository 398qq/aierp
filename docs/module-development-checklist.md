# AIERP 模块开发流程

> 从零开发一个 ERP 模块的完整步骤。以 `ReturnNote`(退货单) 为例。

---

## 总览

```
1.数据模型 → 2.状态机 → 3.Schema → 4.服务层 → 5.API路由 → 6.转换端点 → 7.导出 → 8.测试 → 9.前端
```

---

## 第 1 步: 数据模型

**文件**: `backend/app/models/<domain>.py`

```python
class ReturnNote(TimestampMixin, Base):
    __tablename__ = "return_notes"

    return_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    delivery_note_id: Mapped[int] = mapped_column(ForeignKey("delivery_notes.id"))
    sales_order_id: Mapped[int] = mapped_column(ForeignKey("sales_orders.id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    total_amount: Mapped[float] = mapped_column(DECIMAL(20, 6), default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # 关系
    delivery_note = relationship("DeliveryNote", foreign_keys=[delivery_note_id])
    items = relationship("ReturnNoteItem", back_populates="return_note",
                         lazy="selectin", cascade="all, delete-orphan")

class ReturnNoteItem(TimestampMixin, Base):
    __tablename__ = "return_note_items"
    return_note_id: Mapped[int] = mapped_column(ForeignKey("return_notes.id"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quantity: Mapped[int] = mapped_column(default=1)
    unit_price: Mapped[float | None] = mapped_column(DECIMAL(20, 6), nullable=True)
```

**要点**: `TimestampMixin` 自带 `id, created_at, updated_at, deleted_at`。金额用 `DECIMAL(20,6)`。

---

## 第 2 步: 状态机

**文件**: `backend/app/domain/states/<domain>.py`

```python
RETURN_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"approved", "rejected"},
    "approved": {"completed", "rejected"},
    "completed": set(),
    "rejected": set(),
}

def assert_can_transition_return(current: str, target: str) -> None:
    allowed = RETURN_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidStateTransition(
            f"退货单状态转换非法: {current} → {target}",
            entity="ReturnNote", current=current, target=target,
            allowed=sorted(allowed),
        )
```

**导出**: 在 `domain/states/__init__.py` 的 import 和 `__all__` 中加入新符号。

---

## 第 3 步: Schema

**文件**: `backend/app/schemas/<domain>.py`

```python
class ReturnNoteCreate(BaseModel):
    delivery_note_id: int
    reason: str | None = None

class ReturnNoteUpdate(BaseModel):
    status: str | None = None
    reason: str | None = None

class ReturnNoteResponse(BaseModel):
    id: int; return_no: str | None
    status: str; total_amount: float
    model_config = {"from_attributes": True}
```

---

## 第 4 步: 服务层 (CRUD)

**文件**: `backend/app/services/<domain>_service.py`

```python
async def create_return_note(db: AsyncSession, data: dict) -> ReturnNote:
    if not data.get("return_no"):
        data["return_no"] = await generate_doc_no(db, "RTN", ReturnNote, "return_no")
    note = ReturnNote(**data)
    db.add(note)
    await db.commit(); await db.refresh(note)
    return note

async def update_return_note(db, note, data):
    if "status" in data and data["status"] != note.status:
        assert_can_transition_return(note.status, data["status"])
    for k, v in data.items():
        if v is not None: setattr(note, k, v)
    await db.commit(); await db.refresh(note)
    return note
```

**导出**: 在 `services/__init__.py` 中注册。

---

## 第 5 步: API 路由

**文件**: `backend/app/api/v1/<domain>/crud.py`

```python
router = APIRouter(tags=["return"])

@router.get("/return-notes")
async def list_returns(
    page: int = Query(1, ge=1),
    status: str | None = None,
    db = Depends(get_db), _user = Depends(get_current_user),
):
    result = await svc.list_return_notes(db, page=page, status=status)
    return ok(result)

@router.get("/return-notes/{id}")
async def get_return(id: int, db = Depends(get_db), ...):
    note = await svc.get_return_note(db, id)
    return fail("退货单不存在", 404) if not note else ok(note)

@router.post("/return-notes")
async def create_return(body: ReturnNoteCreate, db = Depends(get_db), ...):
    note = await svc.create_return_note(db, body.model_dump())
    return ok(note)

@router.put("/return-notes/{id}")
async def update_return(id: int, body: ReturnNoteUpdate, db = Depends(get_db), ...):
    note = await svc.get_return_note(db, id)
    if not note: return fail("退货单不存在", 404)
    note = await svc.update_return_note(db, note, body.model_dump(exclude_none=True))
    return ok(note)
```

**注册**: 在 `api/v1/router.py` 中 include_router。

---

## 第 6 步: 转换端点 (跨聚合根)

**文件**: `backend/app/services/<domain>_service/conversions.py`

```python
async def convert_delivery_to_return(db, note, reason=""):
    """发货 → 退货: 创建退货单 + 复制行项目"""
    if note.status not in ("shipped", "delivered"): return None
    # 防重复
    existing = await db.execute(
        select(func.count()).where(ReturnNote.delivery_note_id == note.id, ...))
    if existing.scalar(): return None
    # 创建
    rn = ReturnNote(delivery_note_id=note.id, ..., status="approved", reason=reason)
    db.add(rn); await db.flush()
    for item in note.items:
        db.add(ReturnNoteItem(return_note_id=rn.id, ...))
    await db.commit(); await db.refresh(rn)
    return rn
```

**API**: `POST /delivery-notes/{id}/convert-to-return?reason=xxx`

---

## 第 7 步: 导入/导出

**文件**: `backend/app/api/v1/export_import.py`

```python
# 导出
@router.get("/export/return-notes")
async def export_return_notes(format: str = "csv", ...):
    rows = await db.execute(select(ReturnNote).where(...))
    # → CSV/XLSX

# 导入
@router.post("/import/return-notes")
async def import_return_notes(file: UploadFile = File(...), ...):
    # parse CSV → create records
```

---

## 第 8 步: 测试

```python
# 状态机测试 (单元，无 DB)
class TestReturnNoteStateMachine:
    def test_pending_to_approved(self):
        assert_can_transition_return("pending", "approved")
    def test_completed_is_terminal(self):
        with pytest.raises(InvalidStateTransition):
            assert_can_transition_return("completed", "approved")

# 集成测试 (API + DB)
class TestReturnNoteIntegration:
    async def test_convert_delivery_to_return_success(self, async_client, ...):
        # 创建订单 → 发货 → 转退货 → 验证
```

**运行**: `pytest tests/test_return_note.py -v`

---

## 第 9 步: 前端

### 9.1 Type 定义

```typescript
// frontend/src/types/sales.ts
export interface ReturnNote {
  id: number; return_no: string | null;
  delivery_note_id: number; status: string;
  total_amount: number; reason: string | null;
}
```

### 9.2 API 客户端

```typescript
// frontend/src/api/sales.ts
export const getReturnNotes = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<ReturnNote>>>("/return-notes", { params });
export const createReturnNote = (data: Record<string, unknown>) =>
  client.post<APIResponse<ReturnNote>>("/return-notes", data);
export const convertDeliveryToReturn = (noteId: number, reason?: string) =>
  client.post<APIResponse<...>>(`/delivery-notes/${noteId}/convert-to-return?reason=${reason || ""}`);
```

### 9.3 页面 (List/Detail/Form)

```tsx
// frontend/src/pages/sales/ReturnNoteList.tsx  — 懒加载注册到 App.tsx
const ReturnNoteList = lazy(() => import("./pages/sales/ReturnNoteList"));
// Route: /sales/return-notes
```

### 9.4 测试

```typescript
// frontend/src/test/returnNote.test.tsx
test('renders return note list with status filter', () => {})
test('convert button appears on delivered delivery', () => {})
```

---

## 模块检查清单

- [ ] Model + Item 模型 (`models/`)
- [ ] 状态机定义 + 守卫函数 (`domain/states/`)
- [ ] Schema (Create/Update/Response) (`schemas/`)
- [ ] CRUD 服务 (`services/`)
- [ ] API 路由 (list/get/create/update/delete) + 注册 (`api/v1/`)
- [ ] 转换端点 (如有跨聚合根操作)
- [ ] 导入/导出支持
- [ ] 状态机单元测试
- [ ] API 集成测试 (success + guards + duplicates)
- [ ] TypeScript 类型定义
- [ ] API 客户端函数
- [ ] 前端页面 (List/Detail/Form) + 懒加载注册
- [ ] 前端测试
- [ ] `make lint` + `make test` 全绿

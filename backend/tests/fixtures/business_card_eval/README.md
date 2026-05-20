# Business Card OCR Evaluation Set

This folder stores small JSONL samples for customer business-card recognition.

Each line is one case:

```json
{
  "id": "card-001",
  "raw_text": "best merged OCR text",
  "ocr_candidates": [
    {
      "engine": "rapidocr:original",
      "confidence": 0.91,
      "score": 3.2,
      "key_hits": ["phone", "email", "company"],
      "text": "candidate OCR text"
    }
  ],
  "expected": {
    "name": "深圳市星河电子有限公司",
    "contact_person": "张工",
    "phone": "13800001111",
    "email": "zhang@example.com",
    "address": "深圳市南山区科技园"
  }
}
```

Run the local rule baseline:

```bash
cd backend
python scripts/evaluate_business_card_ocr.py
```

Run through the configured AI model:

```bash
cd backend
python scripts/evaluate_business_card_ocr.py --use-ai
```

Keep real customer secrets out of committed fixtures. Mask phone/email/company names when needed.

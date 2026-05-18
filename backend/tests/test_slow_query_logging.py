import json

from sqlalchemy import text

from app.config import settings
from app.database import _install_slow_query_logging


class TestSlowQueryLogging:
    async def test_logs_when_query_exceeds_threshold(self, engine, caplog, monkeypatch):
        _install_slow_query_logging(engine)
        monkeypatch.setattr(settings, "SLOW_QUERY_THRESHOLD_MS", 0)
        caplog.set_level("WARNING", logger="app.db.slow_query")

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

        slow_records = []
        for record in caplog.records:
            if record.name != "app.db.slow_query":
                continue
            try:
                payload = json.loads(record.message)
            except json.JSONDecodeError:
                continue
            if payload.get("event") == "slow_query":
                slow_records.append(payload)

        assert slow_records
        last = slow_records[-1]
        assert last["threshold_ms"] == 0
        assert "SELECT 1" in last["sql"]
        assert isinstance(last["duration_ms"], float)

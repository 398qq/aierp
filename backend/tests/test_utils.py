"""Tests for shared utility modules: docno, pagination."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestGenerateDocNo:
    @pytest.mark.unit
    async def test_generates_correct_format(self):
        """Document number should follow PREFIX + YYYYMMDD + 0001 format."""
        from app.services.docno import generate_doc_no

        mock_model = MagicMock()
        mock_model.__tablename__ = "quotations"
        mock_col = MagicMock()
        setattr(mock_model, "quotation_no", mock_col)

        db = MagicMock()
        db.get_bind.return_value.dialect.name = "sqlite"

        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.docno.select") as _:
            no = await generate_doc_no(db, "QT", mock_model, "quotation_no")
            assert no.startswith("QT")
            assert len(no) == 14  # QT202605110001 = 14 chars

    @pytest.mark.unit
    async def test_increments_sequence(self):
        """When existing docs found, sequence should increment."""
        from app.services.docno import generate_doc_no

        mock_model = MagicMock()
        mock_model.__tablename__ = "quotations"
        setattr(mock_model, "quotation_no", MagicMock())

        db = MagicMock()
        db.get_bind.return_value.dialect.name = "sqlite"

        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.docno.select") as _:
            no = await generate_doc_no(db, "QT", mock_model, "quotation_no")
            assert no.endswith("0006")  # 5 + 1

    @pytest.mark.unit
    async def test_uses_advisory_lock_on_postgresql(self):
        """PostgreSQL should use pg_advisory_xact_lock."""
        from app.services.docno import generate_doc_no

        mock_model = MagicMock()
        mock_model.__tablename__ = "quotations"
        setattr(mock_model, "quotation_no", MagicMock())

        db = MagicMock()
        db.get_bind.return_value.dialect.name = "postgresql"

        # First call for advisory lock, second for count query
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.docno.select") as _:
            await generate_doc_no(db, "QT", mock_model, "quotation_no")
            # Should have called execute twice: advisory lock + count query
            assert db.execute.call_count >= 2


class TestPaginate:
    @pytest.mark.unit
    async def test_returns_correct_structure(self):
        """paginate should return {list, total, page, page_size}."""
        from app.services.pagination import paginate

        db = MagicMock()
        db.scalar = AsyncMock(return_value=42)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = ["item1", "item2"]
        db.execute = AsyncMock(return_value=mock_result)

        mock_query = MagicMock()
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query

        with patch("app.services.pagination.select") as mock_select:
            mock_select_obj = MagicMock()
            mock_select.return_value = mock_select_obj
            mock_select_obj.select_from.return_value = mock_select_obj

            result = await paginate(db, mock_query, page=1, page_size=20)

        assert "list" in result
        assert "total" in result
        assert "page" in result
        assert "page_size" in result
        assert result["total"] == 42
        assert result["page"] == 1
        assert result["page_size"] == 20

    @pytest.mark.unit
    async def test_handles_empty_result(self):
        """paginate should handle empty results gracefully."""
        from app.services.pagination import paginate

        db = MagicMock()
        db.scalar = AsyncMock(return_value=0)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=mock_result)

        mock_query = MagicMock()
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query

        with patch("app.services.pagination.select") as mock_select:
            mock_select_obj = MagicMock()
            mock_select.return_value = mock_select_obj
            mock_select_obj.select_from.return_value = mock_select_obj

            result = await paginate(db, mock_query, page=1, page_size=20)

        assert result["list"] == []
        assert result["total"] == 0

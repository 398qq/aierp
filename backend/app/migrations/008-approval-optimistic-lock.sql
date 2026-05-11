-- Migration: 008-approval-optimistic-lock.sql
-- Add version column to approval_requests for optimistic locking

ALTER TABLE approval_requests ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 0;

-- Also backfill version = 0 for existing rows (already the default)

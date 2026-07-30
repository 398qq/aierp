-- 011_user_preferences.sql
-- Per-(user, scope, key) JSON value store. Used to sync
-- column_visibility / saved_views etc across devices.

CREATE TABLE IF NOT EXISTS user_preferences (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    scope       VARCHAR(64) NOT NULL,
    key         VARCHAR(64) NOT NULL,
    value       TEXT NOT NULL DEFAULT 'null',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at  TIMESTAMPTZ
);

-- One row per (user, scope, key) — soft-delete via deleted_at.
CREATE UNIQUE INDEX IF NOT EXISTS uq_user_pref_lookup
    ON user_preferences(user_id, scope, key)
    WHERE deleted_at IS NULL;

-- For list-by-scope reads (e.g. GET /prefs/products).
CREATE INDEX IF NOT EXISTS ix_user_pref_scope_key
    ON user_preferences(scope, key)
    WHERE deleted_at IS NULL;

-- For lookups scoped to a user.
CREATE INDEX IF NOT EXISTS ix_user_pref_user_scope
    ON user_preferences(user_id, scope)
    WHERE deleted_at IS NULL;

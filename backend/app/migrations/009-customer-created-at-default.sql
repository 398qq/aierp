-- Ensure customers always have a creation timestamp.
-- Some existing deployments created the column without a database default,
-- leaving imported or newly inserted rows with NULL created_at.

ALTER TABLE customers
    ALTER COLUMN created_at SET DEFAULT NOW();

UPDATE customers
SET created_at = COALESCE(updated_at, NOW())
WHERE created_at IS NULL;

ALTER TABLE customers
    ALTER COLUMN created_at SET NOT NULL;

"""drop jwt_tokens user_id foreign key

Removes the database-level FK constraint between jwt_tokens.user_id and users.id.
CACL intentionally does not maintain a DB-level FK to the users table so that
application models are not forced to share CACL's SQLAlchemy Base.

Token security is preserved: verify_jwt_token() still loads the current user and
rejects the token if the user does not exist or is inactive.

Applications that hard-delete users should delete the related jwt_tokens rows
in their application layer or run a periodic cleanup job.

Revision ID: a1b2c3d4e5f6
Revises: 0366911d4569
Create Date: 2026-05-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '0366911d4569'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the FK constraint.
    # PostgreSQL names an anonymous ForeignKeyConstraint as <table>_<col>_fkey.
    # The init migration did not supply an explicit constraint name, so PostgreSQL
    # assigned 'jwt_tokens_user_id_fkey'.  We use op.execute() with a direct SQL
    # DROP so that the migration is safe even if the constraint name differs
    # across environments (e.g. an existing DB created before this naming
    # convention was assumed).
    op.execute(
        """
        DO $$
        DECLARE
            _constraint_name text;
        BEGIN
            SELECT conname
              INTO _constraint_name
              FROM pg_constraint
              JOIN pg_class ON pg_class.oid = pg_constraint.conrelid
             WHERE pg_class.relname = 'jwt_tokens'
               AND contype = 'f'
               AND pg_constraint.conkey = ARRAY[
                     (SELECT attnum FROM pg_attribute
                       WHERE attrelid = pg_class.oid AND attname = 'user_id')
                   ]::smallint[]
             LIMIT 1;

            IF _constraint_name IS NOT NULL THEN
                EXECUTE format('ALTER TABLE jwt_tokens DROP CONSTRAINT %I', _constraint_name);
            END IF;
        END
        $$;
        """
    )

    # Add a plain index on user_id for efficient lookup/cleanup by user.
    # Use IF NOT EXISTS so re-running the migration is idempotent.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_jwt_tokens_user_id ON jwt_tokens (user_id);"
    )


def downgrade() -> None:
    # Re-add the FK (best-effort: only works if all jwt_tokens.user_id values
    # still reference existing users rows).
    op.execute("DROP INDEX IF EXISTS ix_jwt_tokens_user_id;")
    op.create_foreign_key(
        constraint_name='jwt_tokens_user_id_fkey',
        source_table='jwt_tokens',
        referent_table='users',
        local_cols=['user_id'],
        remote_cols=['id'],
        ondelete='CASCADE',
    )

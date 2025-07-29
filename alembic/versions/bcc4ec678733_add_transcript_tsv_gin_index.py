"""add transcript_tsv GIN index

Revision ID: bcc4ec678733
Revises: 59654d61e5ae
Create Date: 2025-07-29 12:15:45.615039

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TSVECTOR

# revision identifiers, used by Alembic.
revision = 'bcc4ec678733'
down_revision = '59654d61e5ae'
branch_labels = None
depends_on = None
table = 'calls_db'

def upgrade():
    # 1. Install the pg_trgm extension (no-op if already installed)
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    # 2. Add a tsvector column for full-text search
    op.add_column(
        table,
        sa.Column('transcript_tsv', TSVECTOR(), nullable=True)
    )

    # 3. Populate the new column using to_tsvector on existing data
    op.execute(
        "UPDATE calls_db SET transcript_tsv = to_tsvector('english', transcript);"
    )

    # 4. Create a GIN index on the tsvector column
    op.create_index(
        'ix_calls_transcript_tsv',
        table,
        ['transcript_tsv'],
        postgresql_using='gin'
    )

    # 5. (Optional) Add a comment explaining the choice
    op.execute(
        "COMMENT ON INDEX ix_calls_transcript_tsv "
        "IS 'GIN index over english tsvector for fast full-text search';"
    )


def downgrade():
    # Remove the index and column on downgrade
    op.drop_index('ix_calls_transcript_tsv', table_name=table)
    op.drop_column(table, 'transcript_tsv')
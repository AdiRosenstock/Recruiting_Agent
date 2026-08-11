"""outreach_messages created_at uses clock_timestamp

Revision ID: 7794904bb6f8
Revises: 08e24994ab76
Create Date: 2026-08-11 18:15:00.513690

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7794904bb6f8'
down_revision: Union[str, Sequence[str], None] = '08e24994ab76'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Autogenerate doesn't diff raw-SQL server_default expressions, so this is hand-written.
    # now() is frozen for the whole enclosing transaction in Postgres -- multiple
    # outreach_messages rows inserted in one request (a generation always creates 3 at once)
    # used to get an identical created_at, breaking "order by created_at" queries that need to
    # tell two separate generations apart (see api/routers/outreach.py's get_latest_outreach).
    # clock_timestamp() is real wall-clock time and keeps advancing within a transaction.
    op.alter_column(
        "outreach_messages",
        "created_at",
        server_default=sa.text("clock_timestamp()"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "outreach_messages",
        "created_at",
        server_default=sa.text("now()"),
    )

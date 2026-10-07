"""Verified identities, revocable sessions and conservative questionnaire classification."""
from alembic import op
import sqlalchemy as sa

revision = "20261006_privacy_controls"
down_revision = "37d102ca7e27"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user") as batch:
        batch.add_column(sa.Column("auth_version", sa.Integer(), nullable=False, server_default="1"))
        batch.add_column(sa.Column("google_subject", sa.String(255)))
        batch.create_unique_constraint("uq_user_google_subject", ["google_subject"])
        batch.add_column(sa.Column("verification_issued_at", sa.DateTime(timezone=True)))
    # Old links had no expiration and stored raw bearer credentials.
    op.execute("UPDATE user SET verification_token = NULL")
    with op.batch_alter_table("course") as batch:
        batch.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()))
    with op.batch_alter_table("questionnaire") as batch:
        batch.add_column(sa.Column("requires_sensitive_approval", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_table("auth_attempts", sa.Column("key", sa.String(64), primary_key=True),
                    sa.Column("hits", sa.Integer(), nullable=False), sa.Column("expires_at", sa.Integer(), nullable=False))
    op.create_index("ix_auth_attempts_expires_at", "auth_attempts", ["expires_at"])


def downgrade():
    op.drop_table("auth_attempts")
    with op.batch_alter_table("questionnaire") as batch:
        batch.drop_column("requires_sensitive_approval")
    with op.batch_alter_table("course") as batch:
        batch.drop_column("updated_at")
    with op.batch_alter_table("user") as batch:
        batch.drop_constraint("uq_user_google_subject", type_="unique")
        batch.drop_column("verification_issued_at")
        batch.drop_column("google_subject")
        batch.drop_column("auth_version")

"""add persistent agent loop tables and run lifecycle

Revision ID: 20260714_agent_loop
Revises:
Create Date: 2026-07-14
"""

from alembic import op
import sqlalchemy as sa


revision = "20260714_agent_loop"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("agent_sessions") as batch_op:
        batch_op.add_column(
            sa.Column("status", sa.String(length=32), nullable=False, server_default="queued")
        )
        batch_op.add_column(
            sa.Column("max_steps", sa.Integer(), nullable=False, server_default="12")
        )
        batch_op.add_column(
            sa.Column("steps_taken", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(sa.Column("failure_reason", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("started_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("completed_at", sa.DateTime(), nullable=True))
        batch_op.create_index("ix_agent_sessions_status", ["status"], unique=False)

    op.create_table(
        "agent_steps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("agent_sessions.id"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("decision_type", sa.String(length=32), nullable=False),
        sa.Column("tool_name", sa.String(length=100), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("decision_payload", sa.Text(), nullable=False),
        sa.Column("observation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_agent_steps_session_id", "agent_steps", ["session_id"])

    with op.batch_alter_table("agent_tool_calls") as batch_op:
        batch_op.add_column(sa.Column("step_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_agent_tool_calls_step_id_agent_steps",
            "agent_steps",
            ["step_id"],
            ["id"],
        )
        batch_op.create_index("ix_agent_tool_calls_step_id", ["step_id"], unique=False)

    op.create_table(
        "remediation_executions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("agent_sessions.id"), nullable=False),
        sa.Column("step_id", sa.Integer(), sa.ForeignKey("agent_steps.id"), nullable=True),
        sa.Column("action_type", sa.String(length=100), nullable=False),
        sa.Column("service_name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_remediation_executions_session_id",
        "remediation_executions",
        ["session_id"],
    )
    op.create_index(
        "ix_remediation_executions_step_id",
        "remediation_executions",
        ["step_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_remediation_executions_step_id", table_name="remediation_executions")
    op.drop_index("ix_remediation_executions_session_id", table_name="remediation_executions")
    op.drop_table("remediation_executions")
    with op.batch_alter_table("agent_tool_calls") as batch_op:
        batch_op.drop_index("ix_agent_tool_calls_step_id")
        batch_op.drop_constraint(
            "fk_agent_tool_calls_step_id_agent_steps",
            type_="foreignkey",
        )
        batch_op.drop_column("step_id")
    op.drop_index("ix_agent_steps_session_id", table_name="agent_steps")
    op.drop_table("agent_steps")
    with op.batch_alter_table("agent_sessions") as batch_op:
        batch_op.drop_index("ix_agent_sessions_status")
        batch_op.drop_column("completed_at")
        batch_op.drop_column("started_at")
        batch_op.drop_column("failure_reason")
        batch_op.drop_column("steps_taken")
        batch_op.drop_column("max_steps")
        batch_op.drop_column("status")

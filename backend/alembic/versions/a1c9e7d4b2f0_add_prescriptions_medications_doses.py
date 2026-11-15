"""add prescriptions, medications and dose logs

Revision ID: a1c9e7d4b2f0
Revises: 38f4949b1bd4
Create Date: 2026-11-14 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1c9e7d4b2f0'
down_revision: Union[str, Sequence[str], None] = '38f4949b1bd4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'prescriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=True),
        sa.Column('stored_filename', sa.String(length=255), nullable=False),
        sa.Column('content_type', sa.String(length=50), nullable=False),
        sa.Column('language', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('error_message', sa.String(length=500), nullable=True),
        sa.Column('doctor_name', sa.String(length=200), nullable=True),
        sa.Column('diagnosis', sa.String(length=500), nullable=True),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('warnings', sa.JSON(), nullable=False),
        sa.Column('follow_up', sa.String(length=500), nullable=True),
        sa.Column('confidence', sa.String(length=20), nullable=True),
        sa.Column('ai_provider', sa.String(length=30), nullable=True),
        sa.Column('needs_review', sa.Boolean(), nullable=False),
        sa.Column('reviewed_by_id', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['patient_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_prescriptions_id'), 'prescriptions', ['id'], unique=False)
    op.create_index(op.f('ix_prescriptions_patient_id'), 'prescriptions', ['patient_id'], unique=False)

    op.create_table(
        'medications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('prescription_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('dose', sa.String(length=100), nullable=True),
        sa.Column('frequency_per_day', sa.Integer(), nullable=False),
        sa.Column('times', sa.JSON(), nullable=False),
        sa.Column('duration_days', sa.Integer(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('food', sa.String(length=20), nullable=False),
        sa.Column('instructions_simple', sa.Text(), nullable=True),
        sa.Column('instructions_original', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['prescription_id'], ['prescriptions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_medications_id'), 'medications', ['id'], unique=False)
    op.create_index(op.f('ix_medications_prescription_id'), 'medications', ['prescription_id'], unique=False)

    op.create_table(
        'dose_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('medication_id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('scheduled_date', sa.Date(), nullable=False),
        sa.Column('scheduled_time', sa.String(length=5), nullable=False),
        sa.Column('taken_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['medication_id'], ['medications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['patient_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('medication_id', 'scheduled_date', 'scheduled_time', name='uq_dose_slot'),
    )
    op.create_index(op.f('ix_dose_logs_medication_id'), 'dose_logs', ['medication_id'], unique=False)
    op.create_index(op.f('ix_dose_logs_patient_id'), 'dose_logs', ['patient_id'], unique=False)


def downgrade() -> None:
    op.drop_table('dose_logs')
    op.drop_table('medications')
    op.drop_table('prescriptions')

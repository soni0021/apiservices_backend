"""add flexible pricing and multi service keys

Revision ID: flexible_pricing_001
Revises: 48028b63f80d
Create Date: 2024-11-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'flexible_pricing_001'
down_revision = '48028b63f80d'
branch_labels = None
depends_on = None


def upgrade():
    # Add price_per_credit to users table
    op.add_column('users', sa.Column('price_per_credit', sa.Numeric(precision=10, scale=2), nullable=False, server_default='5.0'))
    
    # Make api_keys.service_id nullable to support multi-service keys
    op.alter_column('api_keys', 'service_id',
                    existing_type=sa.String(),
                    nullable=True)
    
    # Add allowed_services to api_keys table for multi-service access
    op.add_column('api_keys', sa.Column('allowed_services', sa.JSON(), nullable=True))
    
    # Add success flag to usage_logs to track only successful calls
    op.add_column('api_usage_logs', sa.Column('success', sa.Boolean(), nullable=False, server_default='false'))
    
    # Update credits_deducted default to 0.0 (will be set based on success)
    op.alter_column('api_usage_logs', 'credits_deducted',
                    existing_type=sa.Numeric(precision=10, scale=2),
                    server_default='0.0')


def downgrade():
    # Remove new columns
    op.drop_column('users', 'price_per_credit')
    op.drop_column('api_keys', 'allowed_services')
    op.drop_column('api_usage_logs', 'success')
    
    # Revert api_keys.service_id to not nullable
    op.alter_column('api_keys', 'service_id',
                    existing_type=sa.String(),
                    nullable=False)
    
    # Revert credits_deducted default
    op.alter_column('api_usage_logs', 'credits_deducted',
                    existing_type=sa.Numeric(precision=10, scale=2),
                    server_default='1.0')


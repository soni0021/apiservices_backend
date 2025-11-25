"""add whitelist urls to api keys

Revision ID: whitelist_urls_001
Revises: flexible_pricing_001
Create Date: 2024-11-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'whitelist_urls_001'
down_revision = 'flexible_pricing_001'
branch_labels = None
depends_on = None


def upgrade():
    # Add whitelist_urls to api_keys table
    op.add_column('api_keys', sa.Column('whitelist_urls', sa.JSON(), nullable=True))


def downgrade():
    # Remove whitelist_urls column
    op.drop_column('api_keys', 'whitelist_urls')


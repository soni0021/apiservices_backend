"""add encrypted key to api keys

Revision ID: encrypted_key_001
Revises: whitelist_urls_001
Create Date: 2024-11-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'encrypted_key_001'
down_revision = 'whitelist_urls_001'
branch_labels = None
depends_on = None


def upgrade():
    # Add encrypted_key to api_keys table (stores full key encrypted for retrieval)
    op.add_column('api_keys', sa.Column('encrypted_key', sa.String(), nullable=True))


def downgrade():
    # Remove encrypted_key column
    op.drop_column('api_keys', 'encrypted_key')


"""Add has_individual_matches column to tournament table

Revision ID: add_individual_matches
Revises: 
Create Date: 2024-03-23 20:58:50.464

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_individual_matches'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Add has_individual_matches column with default value False
    op.add_column('tournament', sa.Column('has_individual_matches', sa.Boolean(), nullable=False, server_default='false'))

def downgrade():
    # Remove the column
    op.drop_column('tournament', 'has_individual_matches') 
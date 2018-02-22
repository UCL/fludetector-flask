"""initial

Revision ID: 539f82b608a7
Revises:
Create Date: 2017-10-13 15:20:33.114128

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '539f82b608a7'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'google_term',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('term', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_google_term_term'), 'google_term', ['term'], unique=True)
    op.create_table(
        'model',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('type', sa.Text(), nullable=False),
        sa.Column('public', sa.Boolean(), nullable=False),
        sa.Column('data', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_model_name'), 'model', ['name'], unique=True)
    op.create_table(
        'twitter_ngram',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ngram', sa.Text(), nullable=False),
        sa.Column('region', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_twitter_ngram_ngram'), 'twitter_ngram', ['ngram'], unique=False)
    op.create_index(op.f('ix_twitter_ngram_region'), 'twitter_ngram', ['region'], unique=False)
    op.create_table(
        'google_score',
        sa.Column('day', sa.Date(), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('term_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['term_id'], ['google_term.id'], ),
        sa.PrimaryKeyConstraint('day', 'term_id')
    )
    op.create_table(
        'model_google_terms',
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('google_term_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['google_term_id'], ['google_term.id'], ),
        sa.ForeignKeyConstraint(['model_id'], ['model.id'], )
    )
    op.create_table(
        'model_score',
        sa.Column('day', sa.Date(), nullable=False),
        sa.Column('region', sa.Text(), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['model_id'], ['model.id'], ),
        sa.PrimaryKeyConstraint('day', 'region', 'model_id')
    )
    op.create_table(
        'model_twitter_ngrams',
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('twitter_ngram_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['model_id'], ['model.id'], ),
        sa.ForeignKeyConstraint(['twitter_ngram_id'], ['twitter_ngram.id'], )
    )
    op.create_table(
        'twitter_score',
        sa.Column('day', sa.Date(), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('ngram_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['ngram_id'], ['twitter_ngram.id'], ),
        sa.PrimaryKeyConstraint('day', 'ngram_id')
    )


def downgrade():
    op.drop_table('twitter_score')
    op.drop_table('model_twitter_ngrams')
    op.drop_table('model_score')
    op.drop_table('model_google_terms')
    op.drop_table('google_score')
    op.drop_index(op.f('ix_twitter_ngram_region'), table_name='twitter_ngram')
    op.drop_index(op.f('ix_twitter_ngram_ngram'), table_name='twitter_ngram')
    op.drop_table('twitter_ngram')
    op.drop_index(op.f('ix_model_name'), table_name='model')
    op.drop_table('model')
    op.drop_index(op.f('ix_google_term_term'), table_name='google_term')
    op.drop_table('google_term')

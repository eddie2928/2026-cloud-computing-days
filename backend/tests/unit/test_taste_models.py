import os

os.environ.setdefault("APP_PASSWORD", "test")
os.environ.setdefault("SESSION_SECRET", "test-secret-key-for-session-signing-32ch")
os.environ.setdefault("DB_URL", "postgresql+asyncpg://u:p@h/d")

from sqlalchemy import UniqueConstraint

from app.models import TasteProfile, User


ARRAY_COLUMNS = [
    "music_genres",
    "favorite_artists",
    "preferred_music_mood",
    "personality_keywords",
    "movie_genres",
    "food_preferences",
    "life_values",
]

NULLABLE_TEXT_COLUMNS = ["mbti", "ideal_type", "weekend_style", "love_language"]


class TestTasteProfileModelStructure:
    def test_tablename(self):
        assert TasteProfile.__tablename__ == "taste_profiles"

    def test_has_required_columns(self):
        cols = {c.key for c in TasteProfile.__table__.columns}
        required = {
            "id", "user_id", "completed", "created_at", "updated_at", "answers",
            *ARRAY_COLUMNS,
            *NULLABLE_TEXT_COLUMNS,
        }
        for col in required:
            assert col in cols, f"Missing column: {col}"

    def test_user_id_unique_constraint(self):
        constraint_cols = set()
        for c in TasteProfile.__table__.constraints:
            if isinstance(c, UniqueConstraint):
                constraint_cols.update(col.name for col in c.columns)
        assert "user_id" in constraint_cols

    def test_array_columns_have_server_default(self):
        for col_name in ARRAY_COLUMNS:
            col = TasteProfile.__table__.c[col_name]
            assert col.server_default is not None, f"{col_name} should have server_default"

    def test_array_columns_not_nullable(self):
        for col_name in ARRAY_COLUMNS:
            col = TasteProfile.__table__.c[col_name]
            assert not col.nullable, f"{col_name} should not be nullable"

    def test_nullable_text_columns(self):
        for col_name in NULLABLE_TEXT_COLUMNS:
            col = TasteProfile.__table__.c[col_name]
            assert col.nullable, f"{col_name} should be nullable"

    def test_completed_server_default(self):
        col = TasteProfile.__table__.c["completed"]
        assert col.server_default is not None

    def test_completed_not_nullable(self):
        col = TasteProfile.__table__.c["completed"]
        assert not col.nullable

    def test_answers_nullable(self):
        col = TasteProfile.__table__.c["answers"]
        assert col.nullable

    def test_created_at_server_default(self):
        col = TasteProfile.__table__.c["created_at"]
        assert col.server_default is not None

    def test_updated_at_server_default(self):
        col = TasteProfile.__table__.c["updated_at"]
        assert col.server_default is not None

    def test_user_relationship_exists(self):
        assert hasattr(TasteProfile, "user")

    def test_user_has_taste_profile_relationship(self):
        assert hasattr(User, "taste_profile")

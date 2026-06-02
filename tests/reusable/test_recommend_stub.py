"""
@reusable
@scope project-local
@description 결정론적 stub 함수의 결정론성·폴백·limit·응답 구조·meta.source 검증 패턴.
             Bedrock 등 실제 AI 연동 후 교체 함수에도 동일 인터페이스 계약 검증으로 재사용 가능.
@usage from app.recommend_stub import recommend_songs 를 실제 recommend 함수로 교체.
       응답 스키마 (items[].query/title/artist/reason, meta.source) 가 유지되는지 확인.
@origin proj_days / agent-task3 (추천 Stub + /api/recommend/songs)
@created 2026-06-02T16:52:14
"""
import pytest

from app.recommend_stub import recommend_songs


class TestRecommendSongsStub:
    def test_determinism_same_input(self):
        taste = {
            "music_genres": ["pop", "jazz"],
            "preferred_music_mood": ["calm"],
            "favorite_artists": ["IU"],
        }
        assert recommend_songs(taste) == recommend_songs(taste)

    def test_determinism_order_independent(self):
        taste_a = {"music_genres": ["pop", "jazz"], "preferred_music_mood": [], "favorite_artists": []}
        taste_b = {"music_genres": ["jazz", "pop"], "preferred_music_mood": [], "favorite_artists": []}
        assert recommend_songs(taste_a) == recommend_songs(taste_b)

    def test_empty_taste_fallback_nonempty(self):
        result = recommend_songs({})
        assert len(result["items"]) > 0

    def test_empty_taste_meta_source(self):
        result = recommend_songs({})
        assert result["meta"]["source"] == "stub"

    def test_limit_default_five(self):
        result = recommend_songs({"music_genres": ["pop"]})
        assert len(result["items"]) == 5

    def test_limit_custom(self):
        result = recommend_songs({"music_genres": ["rock"]}, limit=3)
        assert len(result["items"]) == 3

    def test_limit_one(self):
        result = recommend_songs({"music_genres": ["jazz"]}, limit=1)
        assert len(result["items"]) == 1

    def test_limit_larger_than_pool(self):
        result = recommend_songs({"music_genres": ["pop"]}, limit=25)
        assert len(result["items"]) == 25

    def test_item_structure(self):
        result = recommend_songs({"music_genres": ["indie"]})
        for item in result["items"]:
            assert "query" in item
            assert "title" in item
            assert "artist" in item
            assert "reason" in item
            assert isinstance(item["query"], str)
            assert isinstance(item["title"], str)
            assert isinstance(item["artist"], str)
            assert isinstance(item["reason"], str)

    def test_meta_source_is_stub(self):
        result = recommend_songs({"music_genres": ["rock"], "preferred_music_mood": ["energetic"]})
        assert result["meta"]["source"] == "stub"

    def test_none_fields_treated_as_empty(self):
        taste = {"music_genres": None, "preferred_music_mood": None, "favorite_artists": None}
        result = recommend_songs(taste)
        assert len(result["items"]) > 0
        assert result["meta"]["source"] == "stub"

    def test_missing_fields_treated_as_empty(self):
        result = recommend_songs({"music_genres": ["pop"]})
        assert len(result["items"]) == 5

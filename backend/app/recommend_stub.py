# Claude 연결 시 이 함수를 교체 (app/claude.py 참고)
# 현재는 결정론적 stub 구현 — 실제 AI 추천 없음

import hashlib

_POOL = [
    {"query": "IU 밤편지", "title": "밤편지", "artist": "IU", "reason": "잔잔하고 감성적인 분위기에 어울리는 곡"},
    {"query": "BTS Dynamite", "title": "Dynamite", "artist": "BTS", "reason": "밝고 에너지 넘치는 팝 트랙"},
    {"query": "BLACKPINK How You Like That", "title": "How You Like That", "artist": "BLACKPINK", "reason": "강렬한 K-pop 사운드"},
    {"query": "이적 걱정말아요 그대", "title": "걱정말아요 그대", "artist": "이적", "reason": "위로와 힐링이 되는 곡"},
    {"query": "태연 11:11", "title": "11:11", "artist": "태연", "reason": "감성적인 발라드"},
    {"query": "헤이즈 사랑은 없다", "title": "사랑은 없다", "artist": "헤이즈", "reason": "R&B 무드의 감성 곡"},
    {"query": "BIGBANG 뱅뱅뱅", "title": "뱅뱅뱅", "artist": "BIGBANG", "reason": "신나는 댄스 트랙"},
    {"query": "에픽하이 우산", "title": "우산", "artist": "에픽하이", "reason": "힙합과 감성이 어우러진 명곡"},
    {"query": "볼빨간사춘기 좋다고 말해", "title": "좋다고 말해", "artist": "볼빨간사춘기", "reason": "상큼하고 밝은 인디팝"},
    {"query": "멜로망스 선물", "title": "선물", "artist": "멜로망스", "reason": "따뜻한 감성 발라드"},
    {"query": "악동뮤지션 200%", "title": "200%", "artist": "악동뮤지션", "reason": "경쾌하고 발랄한 팝"},
    {"query": "박효신 야생화", "title": "야생화", "artist": "박효신", "reason": "깊은 감성의 발라드"},
    {"query": "EXO 으르렁", "title": "으르렁", "artist": "EXO", "reason": "강렬한 K-pop 댄스 곡"},
    {"query": "아이유 strawberry moon", "title": "strawberry moon", "artist": "IU", "reason": "몽환적이고 달콤한 무드"},
    {"query": "NCT 127 Kick It", "title": "Kick It", "artist": "NCT 127", "reason": "힙합 기반 강렬한 곡"},
    {"query": "세븐틴 아주 NICE", "title": "아주 NICE", "artist": "세븐틴", "reason": "신나고 즐거운 에너지"},
    {"query": "케이윌 이러지마 제발", "title": "이러지마 제발", "artist": "케이윌", "reason": "애절한 감성 발라드"},
    {"query": "Lim Kim 이름이 뭐에요", "title": "이름이 뭐에요?", "artist": "김예림", "reason": "독특하고 몽환적인 인디"},
    {"query": "giriboy 나쁜 놈", "title": "나쁜 놈", "artist": "기리보이", "reason": "R&B 감성 힙합"},
    {"query": "DAY6 Congratulations", "title": "Congratulations", "artist": "DAY6", "reason": "록 밴드 감성의 K-pop"},
]

_DEFAULT_FALLBACK = [
    {"query": "잔잔한 카페 음악 playlist", "title": "카페에서 (Café Acoustics)", "artist": "Various", "reason": "편안하고 집중력을 높여주는 카페 음악"},
    {"query": "새벽 감성 노래", "title": "새벽 세 시 (3 AM)", "artist": "Various", "reason": "밤 늦은 시간 감성을 자극하는 곡"},
    {"query": "힐링 음악 playlist", "title": "Rest (Healing)", "artist": "Various", "reason": "긴장을 풀어주는 힐링 음악"},
    {"query": "기분 좋아지는 노래", "title": "Happy Vibes", "artist": "Various", "reason": "기분을 업시켜주는 밝은 곡"},
    {"query": "인기 K-pop 2024", "title": "K-pop Hits 2024", "artist": "Various", "reason": "최근 인기 있는 K-pop 모음"},
]


def recommend_songs(taste: dict, limit: int = 5) -> dict:
    genres = sorted(taste.get("music_genres") or [])
    moods = sorted(taste.get("preferred_music_mood") or [])
    artists = sorted(taste.get("favorite_artists") or [])

    if not genres and not moods and not artists:
        items = (_DEFAULT_FALLBACK * ((limit // len(_DEFAULT_FALLBACK)) + 1))[:limit]
        return {"items": items, "meta": {"source": "stub"}}

    seed_str = "|".join(genres + moods + artists)
    seed_int = int(hashlib.md5(seed_str.encode()).hexdigest(), 16)

    offset = seed_int % len(_POOL)
    rotated = _POOL[offset:] + _POOL[:offset]
    items = (rotated * ((limit // len(rotated)) + 1))[:limit]

    return {"items": items, "meta": {"source": "stub"}}

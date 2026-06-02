export const MUSIC_GENRE_OPTIONS = [
  '팝', 'R&B', '힙합', '인디', '록', '재즈', '클래식', '발라드', '일렉트로닉', '국악', 'OST', '기타',
]

export const MUSIC_MOOD_OPTIONS = [
  '잔잔한', '신나는', '감성적인', '집중되는', '몽환적인', '파워풀한',
]

export const MBTI_OPTIONS = [
  'ISTJ', 'ISFJ', 'INFJ', 'INTJ',
  'ISTP', 'ISFP', 'INFP', 'INTP',
  'ESTP', 'ESFP', 'ENFP', 'ENTP',
  'ESTJ', 'ESFJ', 'ENFJ', 'ENTJ',
  '모름',
]

export const MOVIE_GENRE_OPTIONS = [
  '로맨스', '코미디', '액션', '공포', '스릴러', '다큐', '애니메이션', 'SF', '드라마', '판타지',
]

export const LIFE_VALUE_OPTIONS = [
  '자유', '안정', '성장', '관계', '건강', '재미', '성취', '가족', '창의', '정직',
]

export const WEEKEND_STYLE_OPTIONS = [
  '집에서 쉬기', '밖에서 활동하기', '가볍게 나들이', '여행', '혼자만의 시간', '친구/가족과 함께',
]

export const LOVE_LANGUAGE_OPTIONS = [
  '칭찬의 말', '함께하는 시간', '봉사', '선물', '스킨십',
]

export interface TasteFormData {
  music_genres: string[]
  favorite_artists: string[]
  preferred_music_mood: string[]
  mbti: string
  ideal_type: string
  personality_keywords: string[]
  movie_genres: string[]
  food_preferences: string[]
  weekend_style: string
  life_values: string[]
  love_language: string
}

export const EMPTY_TASTE_FORM: TasteFormData = {
  music_genres: [],
  favorite_artists: [],
  preferred_music_mood: [],
  mbti: '',
  ideal_type: '',
  personality_keywords: [],
  movie_genres: [],
  food_preferences: [],
  weekend_style: '',
  life_values: [],
  love_language: '',
}

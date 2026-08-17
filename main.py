import os
import argparse
import json
import requests
from dotenv import load_dotenv
from openai import OpenAI


# -----------------------------
# 기본 설정
# -----------------------------
STYLE_KEYWORDS = {
    "맛집": "맛집",
    "카페": "카페",
    "관광": "관광지",
    "숙소": "숙소",
    "액티비티": "액티비티",
}


# -----------------------------
# 입력 처리
# -----------------------------
def parse_args():
    parser = argparse.ArgumentParser(description="여행지 추천 프로그램")
    parser.add_argument("--region", required=True, help="지역 예: 부산")
    parser.add_argument("--style", required=True, help="스타일 예: 맛집, 카페, 관광")
    parser.add_argument("--budget", required=True, type=int, help="예산(만원 단위)")
    return parser.parse_args()


# -----------------------------
# 임시 추천 데이터
# -----------------------------
def get_fallback_recommendation(region, style, budget):
    return {
        "destination": region,
        "reason": f"{region}은(는) {style} 여행에 잘 맞고, 예산 {budget}만원 기준으로 계획하기 좋아요.",
        "places": build_place_candidates(region, style),
    }


def build_place_candidates(region, style):
    keyword = STYLE_KEYWORDS.get(style, style)
    return [f"{region} {keyword}"]


# -----------------------------
# OpenAI 추천 생성
# -----------------------------
def get_ai_recommendation(region, style, budget):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY가 설정되어 있지 않습니다.")

    client = OpenAI(api_key=api_key)

    prompt = f"""
너는 여행지 추천 도우미야.
사용자 입력:
- 지역: {region}
- 스타일: {style}
- 예산: {budget}만원

아래 형식의 JSON만 출력해:
{{
  "destination": "추천 여행지",
  "reason": "추천 이유",
  "places": ["추천 장소1", "추천 장소2", "추천 장소3"]
}}
"""

    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": "너는 친절한 여행 추천 도우미다."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )

    content = response.choices[0].message.content.strip()

    # 코드블록이 섞여 나올 경우 제거
    if content.startswith("```"):
        content = content.replace("```json", "").replace("```", "").strip()

    return json.loads(content)


# -----------------------------
# Kakao Local API로 장소 검색
# -----------------------------
def search_places_kakao(region, style, size=5):
    kakao_key = os.getenv("KAKAO_REST_API_KEY")
    if not kakao_key:
        raise ValueError("KAKAO_REST_API_KEY가 설정되어 있지 않습니다.")

    keyword = STYLE_KEYWORDS.get(style, style)
    query = f"{region} {keyword}"

    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {
        "Authorization": f"KakaoAK {kakao_key}",
    }
    params = {
        "query": query,
        "size": size,
    }

    response = requests.get(url, headers=headers, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()
    documents = data.get("documents", [])
    return [item["place_name"] for item in documents]


# -----------------------------
# 결과 출력
# -----------------------------
def print_result(region, style, budget, recommendation, places):
    print("입력값:")
    print(f"- 지역: {region}")
    print(f"- 스타일: {style}")
    print(f"- 예산: {budget}만원")
    print()

    print("추천 결과:")
    print(f"추천 여행지: {recommendation.get('destination', region)}")
    print(f"추천 이유: {recommendation.get('reason', '추천 이유를 불러오지 못했습니다.')}")
    print("추천 장소:")
    for place in recommendation.get("places", []):
        print(f"- {place}")
    print()

    print("실제 장소 검색 결과:")
    if places:
        for idx, place in enumerate(places, 1):
            print(f"{idx}. {place}")
    else:
        print("검색 결과가 없습니다.")


# -----------------------------
# 메인 실행
# -----------------------------
def main():
    load_dotenv()
    args = parse_args()

    region = args.region.strip()
    style = args.style.strip()
    budget = args.budget

    try:
        recommendation = get_ai_recommendation(region, style, budget)
    except Exception as e:
        print(f"[경고] OpenAI API 호출 실패: {e}")
        print("[안내] 임시 추천 데이터를 사용합니다.")
        recommendation = get_fallback_recommendation(region, style, budget)

    try:
        places = search_places_kakao(region, style, size=5)
    except Exception as e:
        print(f"[경고] Kakao API 호출 실패: {e}")
        places = []

    print_result(region, style, budget, recommendation, places)


if __name__ == "__main__":
    main()
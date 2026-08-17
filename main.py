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
import argparse
import json
import os
import re
import hashlib
from pathlib import Path
from datetime import datetime

import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)
CACHE_FILE = RESULTS_DIR / "cache.json"

STYLE_KEYWORDS = {
    "힐링": "힐링",
    "맛집": "맛집",
    "액티비티": "액티비티",
    "관광": "관광",
    "자연": "자연",
}

REQUIRED_KEYS = ["destination", "reason", "weather", "events"]

def parse_args():
    parser = argparse.ArgumentParser(
        description="여행지 추천 프로그램",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--region", required=True, help="지역명 예: 서울, 부산")
    parser.add_argument("--style", required=True, help="여행 스타일 예: 힐링, 맛집")
    parser.add_argument("--budget", required=True, type=int, help="예산(숫자)")
    parser.add_argument("--date", required=True, help="여행 날짜 YYYY-MM-DD")
    return parser.parse_args()

def validate_date(date_text):
    try:
        return datetime.strptime(date_text, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("--date 형식이 올바르지 않습니다. 예: 2026-08-17")

def normalize_region(region):
    region = region.strip()
    region = re.sub(r"\s+", " ", region)
    return region

def normalize_style(style):
    style = style.strip()
    return STYLE_KEYWORDS.get(style, style)

def make_cache_key(region, style, budget, date_text):
    raw = f"{region}|{style}|{budget}|{date_text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def load_cache():
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_cache(cache):
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")

def call_openai_with_retry(client, prompt):
    """
    1회 재시도 전략:
    - 1차 응답 JSON 파싱 실패 시
    - 'JSON만 다시 출력' 프롬프트로 1회 재요청
    """
    def _request(p):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "너는 여행 추천 도우미다. 반드시 JSON만 출력한다."},
                {"role": "user", "content": p}
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content

    content = _request(prompt)

    try:
        return json.loads(content)
    except Exception:
        retry_prompt = prompt + "\n\n중요: 위 출력이 JSON 파싱에 실패했어. 반드시 아래 키를 가진 JSON만 다시 출력해.\n" \
                             "destination, reason, weather, events"
        content = _request(retry_prompt)
        return json.loads(content)

def validate_ai_json(data):
    errors = []

    if not isinstance(data, dict):
        return False, ["LLM 응답이 JSON 객체가 아닙니다."]

    for key in REQUIRED_KEYS:
        if key not in data:
            errors.append(f"필수 키 누락: {key}")

    for key in REQUIRED_KEYS:
        if key in data and not isinstance(data[key], (str, list, dict)):
            errors.append(f"타입 오류: {key}")

    return len(errors) == 0, errors

def get_ai_recommendation(region, style, budget, date_text):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None, ["OPENAI_API_KEY가 없습니다."]

    client = OpenAI(api_key=api_key)

    prompt = f"""
아래 조건에 맞는 여행지 추천 JSON을 만들어줘.

조건:
- 지역: {region}
- 여행 스타일: {style}
- 예산: {budget}원
- 날짜: {date_text}

반드시 아래 JSON 형식만 출력:
{{
  "destination": "추천 여행지",
  "reason": "추천 이유",
  "weather": "해당 날짜에 고려할 날씨 설명",
  "events": ["관련 행사/이벤트 1", "관련 행사/이벤트 2"]
}}
"""

    errors = []
    try:
        data = call_openai_with_retry(client, prompt)
    except Exception as e:
        return None, [f"LLM 호출/파싱 실패: {e}"]

    ok, validation_errors = validate_ai_json(data)
    if not ok:
        errors.extend(validation_errors)
        return None, errors

    return data, []

def search_places_kakao(query, size=5):
    """
    destination 우선 검색어 사용
    """
    kakao_key = os.getenv("KAKAO_REST_API_KEY")
    if not kakao_key:
        return [], ["KAKAO_REST_API_KEY가 없습니다."]

    if not query:
        return [], ["검색어가 비어 있습니다."]

    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {kakao_key}"}
    params = {"query": query, "size": size}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        docs = data.get("documents", [])
        return docs, []
    except Exception as e:
        return [], [f"Kakao 검색 실패: {e}"]

def build_markdown_report(input_data, ai_data, places, errors):
    lines = []
    lines.append("# 여행 추천 리포트\n")
    lines.append("## 입력값")
    lines.append(f"- 지역: {input_data['region']}")
    lines.append(f"- 스타일: {input_data['style']}")
    lines.append(f"- 예산: {input_data['budget']}원")
    lines.append(f"- 날짜: {input_data['date']}\n")

    lines.append("## 추천 결과")
    if ai_data:
        lines.append(f"- 추천 여행지: {ai_data.get('destination', '데이터 없음')}")
        lines.append(f"- 추천 이유: {ai_data.get('reason', '데이터 없음')}")
        lines.append(f"- 날씨: {ai_data.get('weather', '데이터 없음')}")
        events = ai_data.get("events", [])
        if isinstance(events, list) and events:
            lines.append("- 이벤트:")
            for ev in events:
                lines.append(f"  - {ev}")
        else:
            lines.append("- 이벤트: 데이터 없음")
    else:
        lines.append("- 데이터 없음")

    lines.append("\n## 맛집/장소 검색")
    if places:
        for p in places:
            name = p.get("place_name", "이름 없음")
            addr = p.get("road_address_name") or p.get("address_name") or "주소 없음"
            lines.append(f"- {name} / {addr}")
    else:
        lines.append("- 데이터 없음")

    lines.append("\n## 에러")
    if errors:
        for e in errors:
            lines.append(f"- {e}")
    else:
        lines.append("- 없음")

    return "\n".join(lines)

def save_results(input_data, ai_data, places, report_md, errors):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    key = make_cache_key(
        input_data["region"], input_data["style"], input_data["budget"], input_data["date"]
    )

    json_path = RESULTS_DIR / f"{timestamp}_{key}.json"
    md_path = RESULTS_DIR / f"{timestamp}_{key}.md"

    result_obj = {
        "input": input_data,
        "ai_recommendation": ai_data if ai_data else {},
        "places": places,
        "errors": errors,
    }

    json_path.write_text(json.dumps(result_obj, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(report_md, encoding="utf-8")

    return str(json_path), str(md_path)

def main():
    args = parse_args()

    errors = []

    try:
        date_obj = validate_date(args.date)
    except ValueError as e:
        print(e)
        return

    region = normalize_region(args.region)
    style = normalize_style(args.style)
    budget = args.budget
    date_text = args.date

    input_data = {
        "region": region,
        "style": style,
        "budget": budget,
        "date": date_text,
    }

    cache_key = make_cache_key(region, style, budget, date_text)
    cache = load_cache()

    # 캐시 재사용
    if cache_key in cache:
        cached = cache[cache_key]
        print("캐시된 결과를 사용합니다.")
        print(cached.get("report_md", ""))
        return

    ai_data, ai_errors = get_ai_recommendation(region, style, budget, date_text)
    errors.extend(ai_errors)

    # destination 우선 검색
    search_query = ""
    if ai_data and ai_data.get("destination"):
        search_query = ai_data["destination"]
    else:
        search_query = region

    places, place_errors = search_places_kakao(search_query, size=5)
    errors.extend(place_errors)

    # 데이터 없음 표기 통일
    if not places:
        print("데이터 없음")

    report_md = build_markdown_report(input_data, ai_data, places, errors)
    json_file, md_file = save_results(input_data, ai_data, places, report_md, errors)

    # 캐시 저장
    cache[cache_key] = {
        "json_file": json_file,
        "md_file": md_file,
        "report_md": report_md,
    }
    save_cache(cache)

    print(report_md)
    print(f"\n저장 완료: {json_file}")
    print(f"저장 완료: {md_file}")

if __name__ == "__main__":
    main()
여행지 추천 프로그램
1. 프로젝트 소개
이 프로젝트는 사용자가 입력한 지역 / 스타일 / 예산을 바탕으로 여행지를 추천하고,
카카오 Local API를 이용해 실제 장소 검색 결과를 출력하는 Python 프로그램입니다.

OpenAI API로 추천을 시도하고,
API 크레딧이 부족할 경우에는 임시 추천 데이터로 자동 대체합니다.

2. 주요 기능
지역, 스타일, 예산 입력 받기
OpenAI 기반 여행지 추천
OpenAI 실패 시 임시 추천 제공
Kakao Local API로 실제 장소 검색
검색 결과 5개 출력
3. 사용 기술
Python 3.14
OpenAI API
Kakao Local API
requests
python-dotenv
argparse
4. 실행 방법
4-1. 가상환경 활성화
powershell
📋 복사
.venv\Scripts\activate
4-2. 패키지 설치
powershell
📋 복사
pip install openai python-dotenv requests
4-3. .env 파일 설정
프로젝트 폴더에 .env 파일을 만들고 아래처럼 입력합니다.

env
📋 복사
OPENAI_API_KEY=여기에_오픈AI_키
KAKAO_REST_API_KEY=여기에_카카오_키
4-4. 프로그램 실행
powershell
📋 복사
python main.py --region 부산 --style 맛집 --budget 30
5. 실행 예시
text
📋 복사
입력값:
- 지역: 부산
- 스타일: 맛집
- 예산: 30만원

추천 결과:
추천 여행지: 부산
추천 이유: ...
추천 장소: ...

실제 장소 검색 결과:
1. 영진돼지국밥 본점
2. 모모스커피 부산본점
3. 합천일류돼지국밥 사상점
4. 빨간떡볶이
5. 평산옥
6. 동작 방식
사용자가 지역, 스타일, 예산을 입력합니다.
OpenAI API로 추천을 요청합니다.
OpenAI 호출에 실패하면 임시 추천 데이터를 사용합니다.
Kakao Local API로 실제 장소를 검색합니다.
결과를 화면에 출력합니다.
7. 참고 사항
현재 OpenAI API는 크레딧 부족 시 임시 추천으로 대체됩니다.
Kakao Local API는 서비스 활성화가 필요합니다.
검색 결과는 지역 및 키워드에 따라 달라질 수 있습니다.

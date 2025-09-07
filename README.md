# 종촌고등학교 도서 검색 시스템

AI 기반 도서 검색 및 추천 시스템입니다.

## 기능

- AI 도서 검색 및 추천
- Gemini AI와 채팅
- 반응형 웹 인터페이스

## 설치 및 실행

1. **저장소 클론**
   ```bash
   git clone https://github.com/PPlI3847/jc_school_lib
   cd jc_school_lib

   ```

2. **의존성 설치**
   ```bash
   pip install -r requirements.txt
   ```

3. **환경 변수 설정**
   ```bash
   cp .env
   ```
   `.env` 파일에서 `GEMINI_API_KEY`를 설정하세요.

   예시
   `GEMINI_API_KEY = Your Gemini Key`

5. **서버 실행**
   ```bash
   python server.py
   ```

6. **접속**
   ```
   http://localhost:3000
   ```

## 설정

### Gemini API 키

[Google AI Studio](https://makersuite.google.com/app/apikey)에서 API 키를 발급받아 `.env` 파일에 설정하세요.

## 파일 구조

```
├── server.py             # FastAPI 서버
├── requirements.txt      # 의존성
├── .env                  # 환경변수 템플릿
├── public/
      ├── index.html      # 메인 페이지
      ├── style.css       # 스타일
      └── script.js       # 클라이언트 코드
```

GitHub에 올라온 index.html, sytle,css, script.js를 public폴더를 생성에 넣은다음 실행하세요

## 기술 스택

- **Backend**: FastAPI, Google Generative AI, Uvicorn
- **Frontend**: JavaScript, CSS3, HTML5

## 라이선스

MIT License

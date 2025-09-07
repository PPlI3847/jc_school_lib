from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
import requests
import json
import os
import glob
from pathlib import Path
from typing import Dict, Any, Optional, List
import google.generativeai as genai
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 서빙 (public 폴더가 있을 때만)
if os.path.exists("public"):
    app.mount("/static", StaticFiles(directory="public"), name="static")

# Gemini API 설정
api_key = os.getenv("GEMINI_API_KEY")
if api_key and api_key != 'your_gemini_api_key_here':
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-pro')
    print("✅ Gemini API 설정 완료")
else:
    model = None
    print("⚠️ GEMINI_API_KEY가 설정되지 않았습니다. AI 채팅 기능은 기본 응답으로 동작합니다.")

class BookSearchRequest(BaseModel):
    npz: str
    meta: str
    query: str
    top_k: int
    source_csv: str
    randomize: bool = True

class ChatRequest(BaseModel):
    message: str

class BookSearchClient:
    def __init__(self, base_url: str = "http://144.24.70.176:8000"):
        self.base_url = base_url
        self.search_endpoint = f"{base_url}/search"
    
    async def search_books(self, query: str, top_k: int, randomize: bool = True) -> Optional[Dict[Any, Any]]:
        payload = {
            "npz": "books_emb.npz",
            "meta": "books_meta.csv",
            "query": query,
            "top_k": top_k,
            "source_csv": "book.csv",
            "randomize": randomize
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            print(f"🔍 검색 중: '{query}' (상위 {top_k}개 결과)")
            response = requests.post(
                self.search_endpoint,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"❌ 도서 검색 API 오류: {e}")
            return None
        except json.JSONDecodeError:
            print("❌ 서버 응답을 JSON으로 파싱할 수 없습니다.")
            return None

# 전역 클라이언트 인스턴스
book_client = BookSearchClient()

def find_file(filename):
    """현재 디렉토리에서 파일 찾기"""
    # 현재 디렉토리에서 찾기
    if os.path.exists(filename):
        return filename
    
    # public 폴더에서 찾기
    public_path = os.path.join('public', filename)
    if os.path.exists(public_path):
        return public_path
    
    # 하위 폴더들에서 찾기
    for root, dirs, files in os.walk('.'):
        if filename in files:
            return os.path.join(root, filename)
    
    return None

def check_requirements():
    """필요한 패키지들이 설치되어 있는지 확인"""
    try:
        import fastapi
        import uvicorn
        import requests
        import google.generativeai
        from dotenv import load_dotenv
        print("✅ 모든 필수 패키지가 설치되어 있습니다.")
        return True
    except ImportError as e:
        print(f"❌ 필수 패키지가 설치되지 않았습니다: {e}")
        print("다음 명령어로 패키지를 설치해주세요:")
        print("pip install -r requirements.txt")
        return False

def check_env_file():
    """환경 변수 파일 확인"""
    env_file = Path('.env')
    if not env_file.exists():
        print("⚠️ .env 파일이 없습니다.")
        print("AI 채팅 기능을 사용하려면:")
        print("1. .env.example 파일을 .env로 복사하세요")
        print("2. .env 파일에서 GEMINI_API_KEY를 실제 API 키로 설정하세요")
        print("3. 도서 검색 기능은 .env 파일 없이도 작동합니다")
        return True  # .env 파일이 없어도 서버 실행 허용
    
    # API 키 확인
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key or api_key == 'your_gemini_api_key_here':
        print("⚠️ GEMINI_API_KEY가 설정되지 않았습니다.")
        print("AI 채팅 기능을 사용하려면:")
        print("1. https://makersuite.google.com/app/apikey 에서 API 키를 발급받으세요")
        print("2. .env 파일에서 GEMINI_API_KEY를 실제 API 키로 설정하세요")
        print("3. 도서 검색 기능은 API 키 없이도 작동합니다")
        return True  # API 키가 없어도 서버 실행 허용
    
    print("✅ 환경 변수가 올바르게 설정되어 있습니다.")
    return True

@app.get("/")
async def read_root():
    """메인 페이지 반환"""
    html_file = find_file('index.html')
    if html_file:
        return FileResponse(html_file)
    
    # HTML 파일이 없으면 기본 페이지
    return Response("""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>도서 검색 및 AI 채팅 서버</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #333; text-align: center; margin-bottom: 30px; }
            .status { padding: 15px; margin: 20px 0; border-radius: 5px; }
            .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .warning { background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
            .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
            ul { margin-left: 20px; }
            .file-list { background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }
            .api-test { margin: 30px 0; }
            .api-test button { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin: 5px; }
            .api-test button:hover { background: #0056b3; }
            #testResult { margin-top: 15px; padding: 15px; background: #f8f9fa; border-radius: 5px; min-height: 50px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 도서 검색 및 AI 채팅 서버</h1>
            
            <div class="status success">
                <strong>✅ 서버가 성공적으로 실행되고 있습니다!</strong>
            </div>
            
            <div class="status warning">
                <strong>⚠️ index.html 파일이 없습니다.</strong><br>
                완전한 웹 인터페이스를 사용하려면 index.html, style.css, script.js 파일을 현재 폴더에 넣어주세요.
            </div>
            
            <div class="file-list">
                <h3>📁 현재 폴더의 파일들:</h3>
                <ul>
    """ + "".join([f"<li>{f}</li>" for f in os.listdir('.')]) + """
                </ul>
            </div>
            
            <div class="api-test">
                <h3>🔧 API 테스트</h3>
                <button onclick="testBookSearch()">도서 검색 테스트</button>
                <button onclick="testChat()">AI 채팅 테스트</button>
                <div id="testResult"></div>
            </div>
        </div>
        
        <script>
            async function testBookSearch() {
                const resultDiv = document.getElementById('testResult');
                resultDiv.innerHTML = '📚 도서 검색 테스트 중...';
                
                try {
                    const response = await fetch('/search', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            npz: "books_emb.npz",
                            meta: "books_meta.csv", 
                            query: "컴퓨터",
                            top_k: 3,
                            source_csv: "book.csv",
                            randomize: true
                        })
                    });
                    
                    const data = await response.json();
                    resultDiv.innerHTML = `
                        <strong>✅ 도서 검색 성공!</strong><br>
                        검색 결과: ${data.results?.length || 0}개<br>
                        <pre>${JSON.stringify(data, null, 2)}</pre>
                    `;
                } catch (error) {
                    resultDiv.innerHTML = `<strong>❌ 도서 검색 실패:</strong> ${error.message}`;
                }
            }
            
            async function testChat() {
                const resultDiv = document.getElementById('testResult');
                resultDiv.innerHTML = '💬 AI 채팅 테스트 중...';
                
                try {
                    const response = await fetch('/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message: "안녕하세요!" })
                    });
                    
                    const data = await response.json();
                    resultDiv.innerHTML = `
                        <strong>✅ AI 채팅 성공!</strong><br>
                        AI 응답: ${data.reply}
                    `;
                } catch (error) {
                    resultDiv.innerHTML = `<strong>❌ AI 채팅 실패:</strong> ${error.message}`;
                }
            }
        </script>
    </body>
    </html>
    """, media_type="text/html")

@app.get("/script.js")
async def get_script():
    script_file = find_file('script.js')
    if script_file:
        return FileResponse(script_file, media_type="application/javascript")
    
    # 기존 script.js가 없으면 새로운 내용으로 생성
    new_script_content = '''
// 업데이트된 script.js
const API_BASE_URL = 'http://localhost:3000';

async function searchBooks(query, topK = 6) {
    try {
        const response = await fetch(`${API_BASE_URL}/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                npz: "books_emb.npz",
                meta: "books_meta.csv",
                query: query,
                top_k: topK,
                source_csv: "book.csv",
                randomize: true
            })
        });
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('검색 오류:', error);
        throw error;
    }
}

async function chatWithGemini(message) {
    try {
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message })
        });
        
        const data = await response.json();
        return data.reply;
    } catch (error) {
        console.error('채팅 오류:', error);
        return 'AI 채팅 중 오류가 발생했습니다.';
    }
}

// 기존 함수들을 수정하여 새로운 API 사용
if (typeof performSearch !== 'undefined') {
    const originalPerformSearch = performSearch;
    performSearch = async function(event) {
        if (event) event.preventDefault();
        
        const searchTerm = document.getElementById('searchInput').value.trim();
        if (!searchTerm) return;
        
        // 기존 UI 로직 유지하면서 새로운 API 호출
        try {
            const isBookSearch = /책|도서|검색|추천/.test(searchTerm);
            
            if (isBookSearch) {
                const results = await searchBooks(searchTerm);
                // 기존 UI 업데이트 로직 호출
                if (typeof addBookGallery !== 'undefined' && results.results) {
                    addBookGallery(results.results);
                }
            } else {
                const response = await chatWithGemini(searchTerm);
                if (typeof addChatMessage !== 'undefined') {
                    addChatMessage('ai', response);
                }
            }
        } catch (error) {
            console.error('검색 오류:', error);
            if (typeof addChatMessage !== 'undefined') {
                addChatMessage('ai', '검색 중 오류가 발생했습니다.');
            }
        }
    };
}

console.log('새로운 API 연결됨');
    '''
    
    return Response(new_script_content, media_type="application/javascript")

@app.get("/style.css")
async def get_style():
    style_file = find_file('style.css')
    if style_file:
        return FileResponse(style_file, media_type="text/css")
    
    # CSS 파일이 없으면 404 대신 빈 CSS 반환
    return Response("/* CSS 파일이 없습니다 */", media_type="text/css")

@app.post("/search")
async def search_books(request: BookSearchRequest):
    """도서 검색 API"""
    try:
        results = await book_client.search_books(
            query=request.query,
            top_k=request.top_k,
            randomize=request.randomize
        )
        
        if results is None:
            # 오류 발생 시 샘플 데이터 반환
            sample_books = [
                {
                    "title": "컴퓨터 과학과 수학의 만남",
                    "author": "김철수",
                    "status": "available",
                    "description": "컴퓨터 과학의 기초가 되는 수학적 개념들을 쉽게 설명한 입문서입니다. 알고리즘의 복잡도 분석부터 암호학의 수학적 원리까지 다룹니다.",
                    "publisher": "한빛미디어",
                    "year": "2023",
                    "category": "컴퓨터공학",
                    "location": "공학도서관 2층",
                    "isbn": "978-89-123-4567-8",
                    "pages": "320"
                },
                {
                    "title": "알고리즘과 이산수학",
                    "author": "이영호",
                    "status": "borrowed",
                    "description": "프로그래밍 알고리즘에 필요한 이산수학의 핵심 개념을 다룹니다. 그래프 이론, 조합론, 논리학 등을 포함합니다.",
                    "publisher": "생록출판",
                    "year": "2022",
                    "category": "수학",
                    "location": "과학도서관 3층",
                    "isbn": "978-89-234-5678-9",
                    "pages": "280"
                },
                {
                    "title": "수학으로 이해하는 인공지능",
                    "author": "박민수",
                    "status": "available",
                    "description": "AI와 머신러닝의 수학적 원리를 고등학생도 이해할 수 있게 설명합니다. 선형대수, 미적분, 확률론의 기초부터 시작합니다.",
                    "publisher": "에이콘출판",
                    "year": "2024",
                    "category": "인공지능",
                    "location": "전산도서관 1층",
                    "isbn": "978-89-345-6789-0",
                    "pages": "400"
                }
            ]
            
            # 요청된 개수만큼 반복하여 다양한 책 생성
            books_to_return = []
            for i in range(min(request.top_k, 10)):  # 최대 10권까지
                book = sample_books[i % len(sample_books)].copy()
                if i >= len(sample_books):
                    book["title"] = f"{book['title']} 제{i+1}권"
                books_to_return.append(book)
            
            return {"results": books_to_return}
        
        return results
        
    except Exception as e:
        print(f"검색 처리 중 오류: {e}")
        raise HTTPException(status_code=500, detail="검색 중 오류가 발생했습니다.")

@app.post("/chat")
async def chat_with_gemini(request: ChatRequest):
    """Gemini와 채팅"""
    try:
        if not model:
            return {"reply": "AI 채팅 기능을 사용하려면 GEMINI_API_KEY를 설정해주세요. 현재는 기본 응답 모드로 동작 중입니다."}
        
        # 도서 검색 관련 질문인지 확인
        search_keywords = ["책", "도서", "검색", "추천", "책 찾기", "도서 찾기"]
        is_book_related = any(keyword in request.message for keyword in search_keywords)
        
        if is_book_related:
            # 도서 관련 질문일 때는 도서 검색도 함께 수행
            search_results = await book_client.search_books(request.message, 3)
            
            # 컨텍스트에 도서 정보 추가
            context = f"""
            사용자 질문: {request.message}
            
            관련 도서 검색 결과:
            {json.dumps(search_results, ensure_ascii=False, indent=2) if search_results else "검색 결과가 없습니다."}
            
            위 도서 정보를 참고하여 도움이 되는 답변을 해주세요. 도서 추천이나 관련 질문에 대해서는 구체적인 도서 정보를 포함하여 답변해주세요.
            """
        else:
            context = request.message
        
        # Gemini API 호출
        response = model.generate_content(context)
        
        return {"reply": response.text}
        
    except Exception as e:
        print(f"Gemini API 오류: {e}")
        return {"reply": "죄송합니다. AI 응답을 생성하는 중 오류가 발생했습니다."}

def startup_checks():
    """서버 시작 시 사전 검사"""
    print("🚀 도서 검색 및 AI 채팅 서버 시작")
    print("=" * 50)
    
    # 필수 패키지 확인
    if not check_requirements():
        print("❌ 필수 패키지를 먼저 설치해주세요.")
        return False
    
    # 환경 변수 확인
    check_env_file()
    
    # 현재 파일들 목록
    print(f"\n📁 현재 폴더의 파일들:")
    for f in sorted(os.listdir('.')):
        if os.path.isfile(f):
            print(f"  - {f}")
    
    print(f"\n🎯 서버 시작...")
    print("=" * 50)
    print("📱 웹 브라우저에서 http://localhost:3000 으로 접속하세요")
    print("🔍 도서 검색: 책 관련 키워드로 검색")
    print("💬 AI 채팅: 일반적인 질문이나 대화")
    print("⚡ 서버를 중지하려면 Ctrl+C 를 누르세요")
    print("=" * 50)
    
    return True

if __name__ == "__main__":
    import uvicorn
    
    if startup_checks():
        try:
            uvicorn.run(app, host="0.0.0.0", port=3000, log_level="info")
        except KeyboardInterrupt:
            print("\n\n👋 서버를 종료합니다.")
        except Exception as e:
            print(f"\n❌ 서버 실행 중 오류가 발생했습니다: {e}")
    else:
        print("\n❌ 서버를 시작할 수 없습니다.")
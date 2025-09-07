function showBookDetails(book) {
    console.log('상세 정보 표시:', book);
    
    let detailsText = `📖 "${book.title}" 상세 정보\n\n`;
    detailsText += `저자: ${book.author}\n`;
    detailsText += `상태: ${book.status === 'available' ? '대출가능' : '대출중'}\n`;

    // 추가 정보가 있을 때만 표시
    if (book.publisher && book.publisher.trim() !== '') {
        detailsText += `출판사: ${book.publisher}\n`;
    }
    if (book.year && book.year.trim() !== '') {
        detailsText += `출판연도: ${book.year}\n`;
    }
    if (book.category && book.category.trim() !== '') {
        detailsText += `분류: ${book.category}\n`;
    }
    if (book.location && book.location.trim() !== '') {
        detailsText += `위치: ${book.location}\n`;
    }
    if (book.isbn && book.isbn.trim() !== '') {
        detailsText += `ISBN: ${book.isbn}\n`;
    }
    if (book.pages && book.pages.trim() !== '') {
        detailsText += `페이지: ${book.pages}\n`;
    }
    
    if (book.description && book.description.trim() !== '' && book.description !== '설명이 없습니다.') {
        detailsText += `\n🔍 내용 소개:\n${book.description}`;
    }

    addChatMessage('ai', detailsText);
}

let isFirstSearch = true;
// API 설정 - Python 서버로 변경
const API_BASE_URL = 'http://localhost:3000';

// 실제 AI API를 통해 도서 검색
async function searchBooks(query, topK = 6) {
    try {
        console.log('🔍 검색 요청:', { query, topK });
        
        const response = await fetch(`${API_BASE_URL}/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                npz: "books_emb.npz",
                meta: "books_meta.csv",
                query: query,
                top_k: topK,
                source_csv: "book.csv",
                randomize: true
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();
        console.log('📥 원본 API 응답:', data);

        // API 응답 구조에 맞게 데이터 변환
        let results = [];
        
        if (Array.isArray(data)) {
            results = data;
        } else if (data && Array.isArray(data.results)) {
            results = data.results;
        } else if (data && typeof data === 'object') {
            results = [data];
        } else {
            throw new Error('예상치 못한 응답 형식');
        }

        // 결과 데이터 정규화
        const normalizedResults = results.map((book, index) => {
            console.log(`📖 도서 #${index + 1} 원본 데이터:`, book);
            
            const normalizedBook = {
                title: book.title || book.제목 || book.book_title || book.name || `도서 #${index + 1}`,
                author: book.author || book.저자 || book.book_author || book.writer || '저자 미상',
                publisher: book.publisher || book.출판사 || book.출판사명 || '',
                year: book.year || book.출판년도 || book.출판연도 || '',
                isbn: book.isbn || book.ISBN || '',
                category: book.category || book.분류 || book.장르 || '',
                pages: book.pages || book.페이지 || book.페이지수 || '',
                location: book.location || book.위치 || book.서가위치 || '',
                status: book.status || (Math.random() > 0.3 ? 'available' : 'borrowed'),
                description: book.description || book.설명 || book.summary || book.내용 || '설명이 없습니다.',
            };

            // 상태 정보 정규화
            if (typeof normalizedBook.status === 'string') {
                const statusLower = normalizedBook.status.toLowerCase();
                if (statusLower.includes('available') || statusLower.includes('가능') || statusLower === '대출가능') {
                    normalizedBook.status = 'available';
                } else if (statusLower.includes('borrowed') || statusLower.includes('대출') || statusLower === '대출중') {
                    normalizedBook.status = 'borrowed';
                }
            }

            return normalizedBook;
        }).filter(book => book.title && book.title.trim() !== '' && !book.title.includes('도서 #'));

        console.log(`📚 최종 처리된 도서 목록: ${normalizedResults.length}권`);

        if (normalizedResults.length === 0) {
            console.warn('⚠️ 유효한 도서 데이터가 없습니다');
            throw new Error('유효한 도서 데이터가 없습니다');
        }

        return { results: normalizedResults };

    } catch (error) {
        console.error('도서 검색 중 오류 발생:', error);
        throw error;
    }
}

// Gemini와 채팅하는 함수
async function chatWithGemini(message) {
    try {
        console.log('💬 Gemini 채팅 요청:', message);
        
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();
        console.log('🤖 Gemini 응답:', data);
        
        return data.reply || '응답을 받을 수 없습니다.';

    } catch (error) {
        console.error('Gemini 채팅 중 오류 발생:', error);
        return 'AI와의 채팅 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
    }
}

// 메시지가 도서 검색 관련인지 확인하는 함수
function isBookSearchQuery(message) {
    const bookKeywords = ['책', '도서', '검색', '찾아', '추천', '책 추천', '도서 추천', '읽고 싶', '소설', '교재', '참고서'];
    return bookKeywords.some(keyword => message.includes(keyword));
}

async function performSearch(event) {
    if (event) event.preventDefault();

    const searchTerm = document.getElementById('searchInput').value.trim();

    if (searchTerm) {
        // 검색 후 입력창 비우기
        document.getElementById('searchInput').value = '';
        resetTextareaHeight();

        if (isFirstSearch) {
            moveSearchBarToTop();
            isFirstSearch = false;
        }

        // 사용자 메시지 추가
        addChatMessage('user', searchTerm);

        // 로딩 메시지 표시
        const loadingMessage = `"${searchTerm}"에 대해 처리하고 있습니다...`;
        const loadingDiv = addChatMessage('ai', loadingMessage);

        try {
            // 도서 검색 관련 쿼리인지 확인
            if (isBookSearchQuery(searchTerm)) {
                // 도서 검색 수행
                const searchResults = await searchBooks(searchTerm);

                // 로딩 메시지 제거
                if (loadingDiv && loadingDiv.parentNode) {
                    loadingDiv.remove();
                }

                // 검색 결과 표시
                const response = `"${searchTerm}"와 관련된 도서를 찾아드렸습니다:`;
                addChatMessage('ai', response);

                if (searchResults && searchResults.results && searchResults.results.length > 0) {
                    addBookGallery(searchResults.results);
                } else {
                    addChatMessage('ai', '죄송합니다. 관련된 도서를 찾을 수 없습니다. 다른 키워드로 검색해보세요.');
                }
            } else {
                // 일반 채팅 (Gemini)
                const aiResponse = await chatWithGemini(searchTerm);

                // 로딩 메시지 제거
                if (loadingDiv && loadingDiv.parentNode) {
                    loadingDiv.remove();
                }

                // AI 응답 표시
                addChatMessage('ai', aiResponse);
            }

        } catch (error) {
            console.error('처리 중 오류:', error);
            
            // 로딩 메시지 제거
            if (loadingDiv && loadingDiv.parentNode) {
                loadingDiv.remove();
            }

            if (isBookSearchQuery(searchTerm)) {
                addChatMessage('ai', '도서 검색 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
            } else {
                addChatMessage('ai', 'AI와의 채팅 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
            }
        }
    }
}

function moveSearchBarToTop() {
    const searchContainer = document.querySelector('.search-container');
    const chatContainer = document.getElementById('chat-container');
    const logo = document.getElementById('logo');
    const searchInput = document.getElementById('searchInput');

    chatContainer.style.display = 'block';
    chatContainer.style.overflowY = 'auto';

    searchInput.placeholder = '무엇이든 물어보세요';

    searchContainer.style.position = 'fixed';
    searchContainer.style.top = '0px';
    searchContainer.style.left = '50%';
    searchContainer.style.transform = 'translateX(-50%)';
    searchContainer.style.maxWidth = '800px';
    searchContainer.style.backgroundColor = '#fff';
    searchContainer.style.borderBottom = '1px solid rgba(0,0,0,0.1)';
    searchContainer.style.padding = '15px 20px';
    searchContainer.style.zIndex = '1000';
    searchContainer.style.width = '100%';

    searchInput.style.marginTop = '-20px';

    logo.style.fontSize = '24px';
    logo.style.marginBottom = '15px';
    logo.style.transition = 'all 0.3s ease';

    const headerHeight = Math.ceil(searchContainer.getBoundingClientRect().height);

    chatContainer.style.position = 'absolute';
    chatContainer.style.top = headerHeight + 'px';
    chatContainer.style.left = '50%';
    chatContainer.style.transform = 'translateX(-50%)';
    chatContainer.style.maxWidth = '960px';
    chatContainer.style.width = '100%';
    chatContainer.style.height = `calc(100vh - ${headerHeight}px)`;
    chatContainer.style.padding = '0';
    chatContainer.style.boxSizing = 'border-box';
}

function addChatMessage(type, message) {
    const chatContainer = document.getElementById('chat-container');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${type}-message`;
    messageDiv.textContent = message;
    chatContainer.appendChild(messageDiv);

    chatContainer.scrollTop = chatContainer.scrollHeight;

    return messageDiv;
}

function addBookGallery(books) {
    console.log('갤러리에 표시할 도서들:', books);
    
    const chatContainer = document.getElementById('chat-container');

    // AI 메시지 컨테이너 생성
    const messageDiv = document.createElement('div');
    messageDiv.className = 'chat-message ai-message';
    messageDiv.style.maxWidth = '700px';
    messageDiv.style.padding = '0';
    messageDiv.style.backgroundColor = 'transparent';

    // 도서 갤러리 생성
    const galleryDiv = document.createElement('div');
    galleryDiv.className = 'book-gallery';

    // 처음 6권만 표시
    const top6Books = books.slice(0, 6);

    if (top6Books.length === 0) {
        const noResultsDiv = document.createElement('div');
        noResultsDiv.textContent = '검색 결과가 없습니다.';
        noResultsDiv.style.padding = '20px';
        noResultsDiv.style.textAlign = 'center';
        noResultsDiv.style.color = '#666';
        messageDiv.appendChild(noResultsDiv);
        chatContainer.appendChild(messageDiv);
        return;
    }

    top6Books.forEach((book, index) => {
        const bookItem = document.createElement('div');
        bookItem.className = 'book-item';
        bookItem.onclick = () => showBookDetails(book);

        const bookCoverHTML = book.image && book.image.trim() !== ''
            ? `<img src="${book.image}" alt="${book.title}" class="book-cover-img" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
               <div class="book-cover" style="display:none;">📚</div>`
            : `<div class="book-cover">📚</div>`;

        const truncatedTitle = book.title.length > 40 ? book.title.substring(0, 40) + '...' : book.title;
        const truncatedAuthor = book.author.length > 20 ? book.author.substring(0, 20) + '...' : book.author;

        bookItem.innerHTML = `
            ${bookCoverHTML}
            <div class="book-title" title="${book.title}">${truncatedTitle}</div>
            <div class="book-author" title="${book.author}">${truncatedAuthor}</div>
            <div class="book-status ${book.status}">${book.status === 'available' ? '대출가능' : '대출중'}</div>
        `;

        galleryDiv.appendChild(bookItem);
    });

    // "더 많은 추천 보기" 버튼 (6권 이상일 때만)
    if (books.length > 6) {
        const moreButton = document.createElement('button');
        moreButton.className = 'more-books-btn';
        moreButton.textContent = `더 많은 추천 보기 (${books.length - 6}권 더)`;
        moreButton.onclick = () => showAllBooks(books);
        messageDiv.appendChild(galleryDiv);
        messageDiv.appendChild(moreButton);
    } else {
        messageDiv.appendChild(galleryDiv);
    }

    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function showAllBooks(books) {
    console.log('전체 도서 모달 표시:', books.length, '권');
    
    const modal = document.getElementById('bookModal');
    const modalTitle = document.getElementById('modalTitle');
    const bookList = document.getElementById('bookList');

    modalTitle.textContent = `전체 추천 도서 목록 (${books.length}권)`;
    bookList.innerHTML = '';

    books.forEach((book, index) => {
        const bookCard = document.createElement('div');
        bookCard.className = 'book-card';
        bookCard.onclick = () => {
            closeModal();
            showBookDetails(book);
        };

        const bookCoverHTML = book.image && book.image.trim() !== ''
            ? `<img src="${book.image}" alt="${book.title}" class="book-cover-img" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
               <div class="book-cover" style="display:none;">📚</div>`
            : `<div class="book-cover">📚</div>`;

        const truncatedDescription = book.description.length > 100 
            ? book.description.substring(0, 100) + '...' 
            : book.description;

        bookCard.innerHTML = `
            ${bookCoverHTML}
            <div class="book-title" title="${book.title}">${book.title}</div>
            <div class="book-author" title="${book.author}">${book.author}</div>
            ${book.publisher ? `<div class="book-publisher">출판사: ${book.publisher}</div>` : ''}
            ${book.year ? `<div class="book-year">출판연도: ${book.year}</div>` : ''}
            ${book.category ? `<div class="book-category">분류: ${book.category}</div>` : ''}
            ${book.location ? `<div class="book-location">위치: ${book.location}</div>` : ''}
            <div class="book-description" title="${book.description}">${truncatedDescription}</div>
            <div class="book-status ${book.status}">${book.status === 'available' ? '대출가능' : '대출중'}</div>
        `;

        bookList.appendChild(bookCard);
    });

    modal.style.display = 'flex';
}

function closeModal() {
    document.getElementById('bookModal').style.display = 'none';
}

function adjustTextareaHeight(textarea) {
    textarea.style.height = '50px';
    
    const scrollHeight = textarea.scrollHeight;
    const maxHeight = 200;
    
    if (scrollHeight > 50) {
        textarea.style.height = Math.min(scrollHeight, maxHeight) + 'px';
    }
    
    if (scrollHeight > maxHeight) {
        textarea.style.overflowY = 'auto';
    } else {
        textarea.style.overflowY = 'hidden';
    }
}

function resetTextareaHeight() {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.style.height = '50px';
        searchInput.style.overflowY = 'hidden';
    }
}

// 초기 로딩 시 이벤트 리스너 등록
document.addEventListener("DOMContentLoaded", () => {
    const searchForm = document.querySelector('.search-box') || document.getElementById('searchForm');
    const searchInput = document.getElementById('searchInput');

    if (searchForm) {
        searchForm.addEventListener('submit', performSearch);
    }

    if (searchInput) {
        searchInput.addEventListener('input', () => {
            adjustTextareaHeight(searchInput);
        });

        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (searchForm) {
                    searchForm.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
                } else {
                    performSearch(new Event('submit'));
                }
            }
        });

        searchInput.addEventListener('focus', () => {
            if (searchInput.value.trim() === '') {
                searchInput.style.height = '50px';
            }
        });
    }

    console.log('DOM 로딩 완료, 이벤트 리스너 등록됨');
});

// 모달 외부 클릭시 닫기
window.onclick = function(event) {
    const modal = document.getElementById('bookModal');
    if (event.target === modal) {
        closeModal();
    }
}
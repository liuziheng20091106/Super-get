"""
365听书 Web 管理界面
"""
from flask import Flask, render_template_string, jsonify, request
import sys
import threading

sys.path.insert(0, '.')

from module.logger import get_logger
from module.manager import Manager
from module.config import Config

app = Flask(__name__)

logger_config = {'console': {'enabled': True, 'level': 'INFO'}}
logger = get_logger('Web', logger_config)
config = Config()
manager = Manager(logger=logger, config=config)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>365听书管理</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        h1 { color: #333; margin-bottom: 20px; }
        .card { background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .search-box { display: flex; gap: 10px; margin-bottom: 20px; }
        input[type="text"] { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 16px; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
        button:hover { background: #0056b3; }
        button:disabled { background: #ccc; cursor: not-allowed; }
        .btn-success { background: #28a745; }
        .btn-success:hover { background: #218838; }
        .btn-warning { background: #ffc107; color: #333; }
        .btn-warning:hover { background: #e0a800; }
        .btn-danger { background: #dc3545; }
        .btn-danger:hover { background: #c82333; }
        .btn-secondary { background: #6c757d; }
        .btn-secondary:hover { background: #5a6268; }
        .book-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
        .book-item { border: 1px solid #eee; border-radius: 8px; padding: 15px; background: #fafafa; }
        .book-title { font-size: 18px; font-weight: bold; margin-bottom: 10px; color: #333; }
        .book-info { font-size: 14px; color: #666; margin-bottom: 10px; }
        .chapter-count { color: #007bff; font-weight: bold; }
        .progress-bar { height: 20px; background: #e9ecef; border-radius: 10px; overflow: hidden; margin: 10px 0; }
        .progress-fill { height: 100%; background: #28a745; transition: width 0.3s; }
        .download-status { font-size: 12px; color: #666; }
        .chapters-list { max-height: 300px; overflow-y: auto; margin-top: 10px; border: 1px solid #eee; }
        .chapter-item { padding: 8px 10px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; font-size: 13px; }
        .chapter-item.downloaded { color: #28a745; }
        .chapter-item.pending { color: #666; }
        .action-btns { display: flex; gap: 5px; margin-top: 10px; flex-wrap: wrap; }
        .action-btns button { font-size: 12px; padding: 5px 10px; }
        .loading { text-align: center; padding: 20px; color: #666; }
        .error { color: #dc3545; padding: 10px; background: #f8d7da; border-radius: 4px; margin-bottom: 10px; }
        .tabs { display: flex; border-bottom: 2px solid #ddd; margin-bottom: 20px; }
        .tab { padding: 10px 20px; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -2px; }
        .tab.active { border-bottom-color: #007bff; color: #007bff; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📚 365听书管理</h1>
        
        <div class="card">
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="输入书名搜索..." onkeypress="if(event.key==='Enter')searchBooks()">
                <button onclick="searchBooks()">搜索</button>
            </div>
            <div id="searchResults"></div>
        </div>

        <div class="tabs">
            <div class="tab active" onclick="switchTab('books')">我的书籍</div>
            <div class="tab" onclick="switchTab('downloads')">下载管理</div>
        </div>

        <div id="booksTab" class="tab-content active">
            <div class="card">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px;">
                    <h3>📖 我的书籍</h3>
                    <button onclick="refreshBooks()">刷新</button>
                </div>
                <div id="bookList" class="book-list"></div>
            </div>
        </div>

        <div id="downloadsTab" class="tab-content">
            <div class="card">
                <h3>⬇️ 下载控制</h3>
                <div class="action-btns">
                    <button id="btnStart" class="btn-success" onclick="startDownload()">开始下载</button>
                    <button class="btn-warning" onclick="pauseDownload()">暂停</button>
                    <button id="btnResume" class="btn-secondary" onclick="resumeDownload()" style="display:none">继续</button>
                    <button class="btn-danger" onclick="cancelDownload()">取消</button>
                </div>
                <div id="downloadStatus" style="margin-top:15px;"></div>
            </div>
        </div>
    </div>

    <script>
        let currentBook = null;

        function switchTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById(tab + 'Tab').classList.add('active');
            if (tab === 'downloads') updateDownloadStatus();
        }

        async function searchBooks() {
            const keyword = document.getElementById('searchInput').value.trim();
            if (!keyword) return;
            
            const div = document.getElementById('searchResults');
            div.innerHTML = '<div class="loading">搜索中...</div>';
            
            try {
                const resp = await fetch('/api/search?q=' + encodeURIComponent(keyword));
                const data = await resp.json();
                
                if (data.error) {
                    div.innerHTML = '<div class="error">' + data.error + '</div>';
                    return;
                }
                
                if (data.length === 0) {
                    div.innerHTML = '<div class="loading">未找到相关书籍</div>';
                    return;
                }
                
                div.innerHTML = data.map(b => `
                    <div class="book-item" style="margin:10px 0;">
                        <div class="book-title">${b.Title}</div>
                        <div class="book-info">章节数: ${b.count}</div>
                        <button class="btn-success" onclick="addBook(${b.id}, '${b.Title}', ${b.count})">添加到我的书籍</button>
                    </div>
                `).join('');
            } catch (e) {
                div.innerHTML = '<div class="error">搜索失败: ' + e.message + '</div>';
            }
        }

        async function addBook(bookId, bookTitle, bookCount) {
            const resp = await fetch('/api/book/add', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({book_id: bookId, book_title: bookTitle, book_count: bookCount})
            });
            const data = await resp.json();
            alert(data.message || data.error);
            document.getElementById('searchResults').innerHTML = '';
            document.getElementById('searchInput').value = '';
            loadBooks();
        }

        async function loadBooks() {
            const resp = await fetch('/api/books');
            const books = await resp.json();
            const div = document.getElementById('bookList');
            
            if (books.length === 0) {
                div.innerHTML = '<div class="loading">暂无书籍，请先搜索添加</div>';
                return;
            }
            
            div.innerHTML = books.map((b, i) => {
                const downloaded = b.Chapters ? b.Chapters.filter(c => c.downloaded).length : 0;
                const total = b.Chapters ? b.Chapters.length : 0;
                const progress = total > 0 ? Math.round(downloaded / total * 100) : 0;
                
                return `
                    <div class="book-item">
                        <div class="book-title">${b.Title}</div>
                        <div class="book-info">章节数: <span class="chapter-count">${total}</span></div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width:${progress}%"></div>
                        </div>
                        <div class="download-status">已下载: ${downloaded}/${total} (${progress}%)</div>
                        <div class="action-btns">
                            <button onclick="updateChapters(${b.id})">更新章节</button>
                            <button class="btn-success" onclick="downloadBook(${b.id})">下载</button>
                            <button class="btn-danger" onclick="removeBook(${b.id})">删除</button>
                        </div>
                    </div>
                `;
            }).join('');
        }

        async function refreshBooks() {
            await loadBooks();
        }

        async function updateChapters(bookId) {
            const resp = await fetch('/api/book/' + bookId + '/chapters', {method: 'POST'});
            const data = await resp.json();
            alert(data.message || data.error);
            loadBooks();
        }

        async function downloadBook(bookId) {
            const resp = await fetch('/api/download/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({book_id: bookId})
            });
            const data = await resp.json();
            alert(data.message || data.error);
        }

        async function removeBook(bookId) {
            if (!confirm('确定要删除这本书吗?')) return;
            const resp = await fetch('/api/book/' + bookId, {method: 'DELETE'});
            const data = await resp.json();
            alert(data.message || data.error);
            loadBooks();
        }

        async function startDownload() {
            const status = await fetch('/api/download/status').then(r => r.json());
            if (status.is_running && !status.is_paused) {
                alert('下载已在运行中');
                return;
            }
            await fetch('/api/download/start', {method: 'POST'});
            updateDownloadStatus();
        }

        async function pauseDownload() {
            await fetch('/api/download/pause', {method: 'POST'});
            updateDownloadStatus();
        }

        async function resumeDownload() {
            await fetch('/api/download/resume', {method: 'POST'});
            updateDownloadStatus();
        }

        async function cancelDownload() {
            if (!confirm('确定要取消所有下载吗?')) return;
            await fetch('/api/download/cancel', {method: 'POST'});
            updateDownloadStatus();
        }

        async function updateDownloadStatus() {
            const resp = await fetch('/api/download/status');
            const status = await resp.json();
            const div = document.getElementById('downloadStatus');
            
            document.getElementById('btnStart').style.display = (status.is_running && !status.is_paused) ? 'none' : 'inline-block';
            document.getElementById('btnResume').style.display = (status.is_running && status.is_paused) ? 'inline-block' : 'none';
            
            div.innerHTML = `
                <div>总任务: ${status.total}</div>
                <div>待下载: ${status.pending}</div>
                <div>下载中: ${status.downloading}</div>
                <div>已完成: ${status.completed}</div>
                <div>失败: ${status.failed}</div>
                <div>状态: ${status.is_running ? (status.is_paused ? '已暂停' : '运行中') : '已停止'}</div>
            `;
        }

        setInterval(updateDownloadStatus, 2000);
        loadBooks();
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/search')
def search():
    keyword = request.args.get('q', '')
    if not keyword:
        return jsonify([])
    results = manager.search_books(keyword)
    if results is False:
        return jsonify({'error': '搜索失败'})
    return jsonify([{
        'id': r.id,
        'Title': r.bookTitle,
        'count': r.count,
        'Desc': r.bookDesc
    } for r in results])

@app.route('/api/books')
def get_books():
    books = manager.get_books()
    return jsonify([{
        'id': b.id,
        'Title': b.Title,
        'count': b.count,
        'Chapters': [{'id': c.chapterid, 'title': c.title, 'downloaded': c.downloaded} for c in b.Chapters]
    } for b in books])

@app.route('/api/book/add', methods=['POST'])
def add_book():
    data = request.json
    book_id = data.get('book_id')
    book_title = data.get('book_title', '')
    book_count = data.get('book_count', 0)
    
    for book in manager.get_books():
        if book.id == book_id:
            return jsonify({'message': '书籍已存在'})
    
    from module.data_provider import SearchResult
    sr = SearchResult(
        id=book_id,
        bookTitle=book_title,
        bookDesc='',
        bookImage='',
        bookAnchor='',
        count=book_count,
        UpdateStatus=0,
        heat=0
    )
    
    success = manager.add_book(sr)
    if success:
        book = manager.get_book_by_id(book_id)
        if book:
            manager.update_chapters(book)
            manager.save_to_json()
        return jsonify({'message': '添加成功'})
    return jsonify({'error': '添加失败'})

@app.route('/api/book/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    book = manager.get_book_by_id(book_id)
    if book:
        manager.remove_book(book)
        manager.save_to_json()
        return jsonify({'message': '删除成功'})
    return jsonify({'error': '书籍不存在'})

@app.route('/api/book/<int:book_id>/chapters', methods=['POST'])
def update_book_chapters(book_id):
    book = manager.get_book_by_id(book_id)
    if not book:
        return jsonify({'error': '书籍不存在'})
    
    manager.update_chapters(book)
    manager.save_to_json()
    return jsonify({'message': f'已更新 {len(book.Chapters)} 个章节'})

@app.route('/api/download/start', methods=['POST'])
def download_start():
    data = request.json or {}
    book_id = data.get('book_id')
    
    if book_id:
        book = manager.get_book_by_id(book_id)
        if not book:
            return jsonify({'error': '书籍不存在'})
        manager.start_download(book)
    else:
        for book in manager.get_books():
            manager.start_download(book)
    
    return jsonify({'message': '开始下载'})

@app.route('/api/download/pause', methods=['POST'])
def download_pause():
    manager.pause_download()
    return jsonify({'message': '已暂停'})

@app.route('/api/download/resume', methods=['POST'])
def download_resume():
    manager.resume_download()
    return jsonify({'message': '已继续'})

@app.route('/api/download/cancel', methods=['POST'])
def download_cancel():
    manager.cancel_download()
    return jsonify({'message': '已取消'})

@app.route('/api/download/status')
def download_status():
    return jsonify(manager.get_download_status())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

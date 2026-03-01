/**
 * API 接口模块
 * 提供与后端服务通信的所有接口方法
 */

const BASE_URL = '';

/**
 * 发送API请求的通用方法
 * @param {string} endpoint - API端点
 * @param {string} method - HTTP方法
 * @param {Object} params - URL参数
 * @param {Object} data - 请求体数据
 * @returns {Promise<any>} 返回Promise，成功时resolve返回data，失败时reject抛出错误
 */
function request(endpoint, method = 'GET', params = {}, data = null) {
  let url = BASE_URL + endpoint;
  const queryParams = [];

  for (const key in params) {
    if (params[key] !== undefined && params[key] !== null) {
      queryParams.push(`${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`);
    }
  }

  if (queryParams.length > 0) {
    url += '?' + queryParams.join('&');
  }

  const options = {
    method: method,
    headers: {
      'Content-Type': 'application/json'
    }
  };

  if (data) {
    options.body = JSON.stringify(data);
  }

  return fetch(url, options)
    .then(response => response.json())
    .then(result => {
      if (result.status === 'success' || result.status === true) {
        return result.data;
      } else {
        throw new Error(result.message || '请求失败');
      }
    });
}

/**
 * 搜索书籍
 * @param {string} keywords - 搜索关键词
 * @returns {Promise<any>}
 */
export function search(keywords) {
  return request('/search', 'GET', { keywords });
}

/**
 * 获取书籍详情
 * @param {string|number} id - 书籍ID
 * @returns {Promise<any>}
 */
export function getBook(id) {
  return request('/book', 'GET', { id });
}

/**
 * 获取书籍章节列表
 * @param {string|number} bookId - 书籍ID
 * @returns {Promise<any>}
 */
export function getChapters(bookId) {
  return request('/chapter', 'GET', { bookId });
}

/**
 * 编辑章节
 * @param {string|number} bookId - 书籍ID
 * @param {Array} chapters - 章节数组 [{chapterid, title}]
 * @returns {Promise<any>}
 */
export function editChapter(bookId, chapters) {
  return request('/chapter/edit', 'POST', {}, { bookId, chapters });
}

/**
 * 删除章节
 * @param {string|number} bookId - 书籍ID
 * @param {Array} chapterIds - 章节ID数组
 * @returns {Promise<any>}
 */
export function removeChapter(bookId, chapterIds) {
  return request('/chapter/remove', 'POST', {}, { bookId, chapterIds });
}

/**
 * 获取书架列表
 * @returns {Promise<any>}
 */
export function getBookshelf() {
  return request('/bookshelf/get', 'GET');
}

/**
 * 添加书籍到书架
 * @param {string|number} id - 书籍ID
 * @returns {Promise<any>}
 */
export function addToBookshelf(id) {
  return request('/bookshelf/add', 'GET', { id });
}

/**
 * 从书架移除书籍
 * @param {string|number} id - 书籍ID
 * @returns {Promise<any>}
 */
export function removeFromBookshelf(id) {
  return request('/bookshelf/remove', 'GET', { id });
}

/**
 * 获取下载状态
 * @returns {Promise<any>}
 */
export function getDownloadStatus() {
  return request('/download/status', 'GET');
}

/**
 * 添加下载任务
 * @param {Array} tasks - 下载任务数组 [{bookId, chapterId}]
 * @returns {Promise<any>}
 */
export function addDownload(tasks) {
  return request('/download/add', 'POST', {}, { tasks });
}

/**
 * 暂停下载任务
 * @param {Array} tasks - 下载任务数组 [{bookId, chapterId}]
 * @returns {Promise<any>}
 */
export function pauseDownload(tasks) {
  return request('/download/pause', 'POST', {}, { tasks });
}

/**
 * 删除下载任务
 * @param {Array} tasks - 下载任务数组 [{bookId, chapterId}]
 * @returns {Promise<any>}
 */
export function removeDownload(tasks) {
  return request('/download/remove', 'POST', {}, { tasks });
}

/**
 * 开始解析
 * @param {string|number} bookId - 书籍ID
 * @param {Array} chapterIds - 章节ID数组
 * @returns {Promise<any>}
 */
export function startParse(bookId, chapterIds) {
  return request('/parse/start', 'POST', {}, { bookId, chapterIds });
}

/**
 * 批量操作
 * @param {string} action - 操作类型
 * @param {string|number} bookId - 书籍ID
 * @param {Array} chapterIds - 章节ID数组
 * @returns {Promise<any>}
 */
export function startBatch(action, bookId, chapterIds) {
  return request('/batch/start', 'POST', {}, { action, bookId, chapterIds });
}

/**
 * 获取任务进度
 * @returns {Promise<any>}
 */
export function getProgress() {
  return request('/task/progress', 'GET');
}

/**
 * 停止任务
 * @returns {Promise<any>}
 */
export function stopTask() {
  return request('/task/stop', 'POST');
}

/**
 * 获取统计数据
 * @returns {Promise<any>}
 */
export function getStatistics() {
  return request('/task/statistics', 'GET');
}

export default {
  search,
  getBook,
  getChapters,
  editChapter,
  removeChapter,
  getBookshelf,
  addToBookshelf,
  removeFromBookshelf,
  getDownloadStatus,
  addDownload,
  pauseDownload,
  removeDownload,
  startParse,
  startBatch,
  getProgress,
  stopTask,
  getStatistics
};

window.api = {
  search,
  getBook,
  getChapters,
  editChapter,
  removeChapter,
  getBookshelf,
  addToBookshelf,
  removeFromBookshelf,
  getDownloadStatus,
  addDownload,
  pauseDownload,
  removeDownload,
  startParse,
  startBatch,
  getProgress,
  stopTask,
  getStatistics
};

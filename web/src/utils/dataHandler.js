/**
 * 数据处理工具
 * 处理搜索结果、书籍详情、章节列表、下载状态和任务统计数据
 */

import { sanitizeHtml } from './validator.js';

/**
 * 处理搜索结果数据
 * @param {Array} results - 原始搜索结果数组
 * @returns {Array} 处理后的搜索结果数组
 */
function processSearchResults(results) {
  if (!Array.isArray(results)) {
    return [];
  }

  return results.map(item => ({
    id: Number(item.id) || 0,
    bookTitle: sanitizeHtml(String(item.bookTitle || '')),
    bookDesc: sanitizeHtml(String(item.bookDesc || '')),
    bookImage: String(item.bookImage || ''),
    bookAnchor: sanitizeHtml(String(item.bookAnchor || '')),
    count: Number(item.count) || 0,
    UpdateStatus: Number(item.UpdateStatus) || 0,
    heat: Number(item.heat) || 0
  }));
}

/**
 * 处理书籍详情数据
 * @param {Object} book - 原始书籍详情数据
 * @returns {Object|null} 处理后的书籍详情数据
 */
function processBookDetail(book) {
  if (!book || typeof book !== 'object') {
    return null;
  }

  return {
    id: Number(book.id) || 0,
    count: Number(book.count) || 0,
    UpdateStatus: Number(book.UpdateStatus) || 0,
    Image: String(book.Image || ''),
    Desc: sanitizeHtml(String(book.Desc || '')),
    Title: sanitizeHtml(String(book.Title || '')),
    Anchor: sanitizeHtml(String(book.Anchor || '')),
    Chapters: processChapterList(book.Chapters)
  };
}

/**
 * 处理章节列表数据
 * @param {Array} chapters - 原始章节数组
 * @returns {Array} 处理后的章节数组
 */
function processChapterList(chapters) {
  if (!Array.isArray(chapters)) {
    return [];
  }

  return chapters.map(chapter => ({
    chapterid: Number(chapter.chapterid) || 0,
    position: Number(chapter.position) || 0,
    title: sanitizeHtml(String(chapter.title || '')),
    time: String(chapter.time || ''),
    uploadDate: String(chapter.uploadDate || ''),
    url: Number(chapter.url) || 0,
    bookTitle: sanitizeHtml(String(chapter.bookTitle || '')),
    bookid: Number(chapter.bookid) || 0,
    bookAnchor: sanitizeHtml(String(chapter.bookAnchor || '')),
    bookDesc: sanitizeHtml(String(chapter.bookDesc || '')),
    bookImage: String(chapter.bookImage || ''),
    downloaded: Boolean(chapter.downloaded)
  }));
}

/**
 * 处理下载状态数据
 * @param {Array} downloadStatusList - 原始下载状态数组
 * @returns {Array} 处理后的下载状态数组
 */
function processDownloadStatus(downloadStatusList) {
  if (!Array.isArray(downloadStatusList)) {
    return [];
  }

  return downloadStatusList.map(status => ({
    chapterid: Number(status.chapterid) || 0,
    title: sanitizeHtml(String(status.title || '')),
    bookTitle: sanitizeHtml(String(status.bookTitle || '')),
    bookid: Number(status.bookid) || 0,
    downloaded: Boolean(status.downloaded),
    status: String(status.status || 'pending'),
    progress: Number(status.progress) || 0,
    error: sanitizeHtml(String(status.error || ''))
  }));
}

/**
 * 处理任务统计数据
 * @param {Object} stats - 原始统计数据对象
 * @returns {Object} 处理后的统计数据对象
 */
function processTaskStats(stats) {
  if (!stats || typeof stats !== 'object') {
    return {
      total: 0,
      completed: 0,
      failed: 0,
      pending: 0,
      downloading: 0
    };
  }

  return {
    total: Number(stats.total) || 0,
    completed: Number(stats.completed) || 0,
    failed: Number(stats.failed) || 0,
    pending: Number(stats.pending) || 0,
    downloading: Number(stats.downloading) || 0
  };
}

/**
 * 格式化文件大小
 * @param {number} bytes - 字节数
 * @returns {string} 格式化后的文件大小
 */
function formatFileSize(bytes) {
  const size = Number(bytes) || 0;
  if (size === 0) return '0 B';

  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const k = 1024;
  const i = Math.floor(Math.log(size) / Math.log(k));

  return `${(size / Math.pow(k, i)).toFixed(2)} ${units[i]}`;
}

/**
 * 格式化时间戳
 * @param {string|number} timestamp - 时间戳
 * @returns {string} 格式化后的时间字符串
 */
function formatTimestamp(timestamp) {
  if (!timestamp) return '';

  const date = new Date(timestamp);
  if (isNaN(date.getTime())) {
    return String(timestamp);
  }

  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');

  return `${year}-${month}-${day} ${hours}:${minutes}`;
}

export {
  processSearchResults,
  processBookDetail,
  processChapterList,
  processDownloadStatus,
  processTaskStats,
  formatFileSize,
  formatTimestamp
};

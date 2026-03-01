/**
 * 表单验证工具
 * 提供搜索关键词、书籍ID、章节ID的验证以及HTML转义功能
 */

/**
 * 验证搜索关键词
 * @param {string} keyword - 搜索关键词
 * @returns {{valid: boolean, message: string}}
 */
function validateKeyword(keyword) {
  if (keyword === null || keyword === undefined) {
    return { valid: false, message: '关键词不能为空' };
  }

  const keywordStr = String(keyword).trim();

  if (keywordStr.length === 0) {
    return { valid: false, message: '关键词不能为空' };
  }

  if (keywordStr.length > 100) {
    return { valid: false, message: '关键词长度不能超过100个字符' };
  }

  const invalidPattern = /[<>{}[\]\\^~]/;
  if (invalidPattern.test(keywordStr)) {
    return { valid: false, message: '关键词包含非法字符' };
  }

  return { valid: true, message: '验证通过' };
}

/**
 * 验证书籍ID
 * @param {number|string} id - 书籍ID
 * @returns {{valid: boolean, message: string}}
 */
function validateBookId(id) {
  if (id === null || id === undefined) {
    return { valid: false, message: '书籍ID不能为空' };
  }

  const numId = Number(id);

  if (isNaN(numId)) {
    return { valid: false, message: '书籍ID必须是数字' };
  }

  if (!Number.isInteger(numId)) {
    return { valid: false, message: '书籍ID必须是整数' };
  }

  if (numId <= 0) {
    return { valid: false, message: '书籍ID必须是正数' };
  }

  if (numId > 2147483647) {
    return { valid: false, message: '书籍ID超出有效范围' };
  }

  return { valid: true, message: '验证通过' };
}

/**
 * 验证章节ID
 * @param {number|string} id - 章节ID
 * @returns {{valid: boolean, message: string}}
 */
function validateChapterId(id) {
  if (id === null || id === undefined) {
    return { valid: false, message: '章节ID不能为空' };
  }

  const numId = Number(id);

  if (isNaN(numId)) {
    return { valid: false, message: '章节ID必须是数字' };
  }

  if (!Number.isInteger(numId)) {
    return { valid: false, message: '章节ID必须是整数' };
  }

  if (numId <= 0) {
    return { valid: false, message: '章节ID必须是正数' };
  }

  if (numId > 2147483647) {
    return { valid: false, message: '章节ID超出有效范围' };
  }

  return { valid: true, message: '验证通过' };
}

/**
 * HTML转义防止XSS攻击
 * @param {string} html - 需要转义的HTML字符串
 * @returns {string} 转义后的字符串
 */
function sanitizeHtml(html) {
  if (html === null || html === undefined) {
    return '';
  }

  const str = String(html);

  const escapeMap = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#x27;',
    '/': '&#x2F;'
  };

  return str.replace(/[&<>"'/]/g, char => escapeMap[char] || char);
}

export {
  validateKeyword,
  validateBookId,
  validateChapterId,
  sanitizeHtml
};

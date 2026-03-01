/**
 * app.js - 应用入口
 * 初始化页面、绑定全局事件、启动应用
 */

(function() {
  'use strict';

  let mainPage = null;

  /**
   * 初始化应用程序
   */
  function initApp() {
    console.log('[应用] 正在初始化听书下载管理器...');

    initComponents();
    initGlobalEvents();
    initMainPage();

    console.log('[应用] 初始化完成');
  }

  /**
   * 初始化组件
   */
  function initComponents() {
    console.log('[应用] 初始化组件...');
  }

  /**
   * 初始化全局事件
   */
  function initGlobalEvents() {
    console.log('[应用] 绑定全局事件...');

    window.addEventListener('beforeunload', handleBeforeUnload);

    window.addEventListener('error', handleGlobalError);

    window.addEventListener('unhandledrejection', handleUnhandledRejection);

    document.addEventListener('DOMContentLoaded', () => {
      console.log('[应用] DOM加载完成');
    });
  }

  /**
   * 初始化主页面
   */
  function initMainPage() {
    try {
      mainPage = new MainPage({
        api: window.api,
      });
      mainPage.init();
      console.log('[应用] 主页面已启动');
    } catch (error) {
      console.error('[应用] 主页面初始化失败:', error);
      showInitError('页面初始化失败，请刷新页面重试');
    }
  }

  /**
   * 页面关闭前处理
   * @param {BeforeUnloadEvent} event - 关闭事件
   */
  function handleBeforeUnload(event) {
    if (mainPage && mainPage.isProcessing) {
      const message = '有任务正在执行中，确定要离开吗？';
      event.preventDefault();
      event.returnValue = message;
      return message;
    }
  }

  /**
   * 全局错误处理
   * @param {ErrorEvent} event - 错误事件
   */
  function handleGlobalError(event) {
    console.error('[应用] 全局错误:', event.error);
  }

  /**
   * 未处理的Promise拒绝
   * @param {PromiseRejectionEvent} event - 拒绝事件
   */
  function handleUnhandledRejection(event) {
    console.error('[应用] 未处理的Promise拒绝:', event.reason);
  }

  /**
   * 显示初始化错误
   * @param {string} message - 错误消息
   */
  function showInitError(message) {
    const app = document.getElementById('app');
    if (app) {
      app.innerHTML = `
        <div class="init-error">
          <h2>⚠️ 初始化错误</h2>
          <p>${message}</p>
          <button onclick="location.reload()">刷新页面</button>
        </div>
      `;
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
  } else {
    initApp();
  }

  window.addEventListener('load', () => {
    console.log('[应用] 页面资源全部加载完成');
  });

})();

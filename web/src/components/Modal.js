/**
 * Modal - 模态框组件
 * 提供显示/隐藏模态框功能，支持点击遮罩关闭和ESC键关闭
 */
class Modal {
  /**
   * 初始化模态框
   * @param {string} id - 模态框元素ID
   * @param {Object} options - 配置选项
   */
  constructor(id, options = {}) {
    this.id = id;
    this.element = document.getElementById(id);
    this.options = {
      closeOnOverlayClick: options.closeOnOverlayClick !== false,
      closeOnEsc: options.closeOnEsc !== false,
      onClose: options.onClose || null,
      onOpen: options.onOpen || null,
    };
    this.isVisible = false;
    this.init();
  }

  /**
   * 初始化事件监听
   */
  init() {
    if (!this.element) return;

    const overlay = this.element.querySelector('.modal-overlay');
    const closeBtn = this.element.querySelector('.modal-close');

    if (closeBtn) {
      closeBtn.addEventListener('click', () => this.hide());
    }

    if (overlay && this.options.closeOnOverlayClick) {
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
          this.hide();
        }
      });
    }

    if (this.options.closeOnEsc) {
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && this.isVisible) {
          this.hide();
        }
      });
    }
  }

  /**
   * 显示模态框
   */
  show() {
    if (!this.element) return;
    this.element.style.display = 'flex';
    this.isVisible = true;
    if (this.options.onOpen) {
      this.options.onOpen();
    }
  }

  /**
   * 隐藏模态框
   */
  hide() {
    if (!this.element) return;
    this.element.style.display = 'none';
    this.isVisible = false;
    if (this.options.onClose) {
      this.options.onClose();
    }
  }

  /**
   * 切换显示状态
   */
  toggle() {
    if (this.isVisible) {
      this.hide();
    } else {
      this.show();
    }
  }

  /**
   * 设置内容
   * @param {string} content - HTML内容
   */
  setContent(content) {
    const contentEl = this.element.querySelector('.modal-content');
    if (contentEl) {
      contentEl.innerHTML = content;
    }
  }

  /**
   * 获取内容元素
   * @returns {HTMLElement|null}
   */
  getContentElement() {
    return this.element ? this.element.querySelector('.modal-content') : null;
  }
}

export default Modal;

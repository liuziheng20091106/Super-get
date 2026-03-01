/**
 * ProgressBar - 进度条组件
 * 提供设置进度值、设置进度文本、显示/隐藏功能
 */
class ProgressBar {
  /**
   * 初始化进度条
   * @param {string} id - 进度条元素ID
   * @param {Object} options - 配置选项
   */
  constructor(id, options = {}) {
    this.id = id;
    this.element = document.getElementById(id);
    this.options = {
      showText: options.showText !== false,
      striped: options.striped || false,
      animated: options.animated || false,
      onComplete: options.onComplete || null,
    };
    this.value = 0;
    this.max = 100;
    this.text = '';
    this.isVisible = false;
    this.init();
  }

  /**
   * 初始化进度条元素
   */
  init() {
    if (!this.element) return;

    if (!this.element.querySelector('.progress-bar-inner')) {
      const inner = document.createElement('div');
      inner.className = 'progress-bar-inner';
      this.element.appendChild(inner);
    }

    if (!this.element.querySelector('.progress-bar-text')) {
      const text = document.createElement('div');
      text.className = 'progress-bar-text';
      this.element.appendChild(text);
    }

    if (this.options.striped) {
      this.element.classList.add('progress-striped');
    }
    if (this.options.animated) {
      this.element.classList.add('progress-animated');
    }
  }

  /**
   * 设置进度值
   * @param {number} value - 进度值 (0-100)
   */
  setValue(value) {
    this.value = Math.max(0, Math.min(100, value));
    this.updateBar();
    if (this.value >= 100 && this.options.onComplete) {
      this.options.onComplete();
    }
  }

  /**
   * 获取当前进度值
   * @returns {number}
   */
  getValue() {
    return this.value;
  }

  /**
   * 设置最大进度值
   * @param {number} max - 最大进度值
   */
  setMax(max) {
    this.max = max;
    this.updateBar();
  }

  /**
   * 获取最大进度值
   * @returns {number}
   */
  getMax() {
    return this.max;
  }

  /**
   * 设置进度文本
   * @param {string} text - 进度文本
   */
  setText(text) {
    this.text = text;
    const textEl = this.element.querySelector('.progress-bar-text');
    if (textEl) {
      textEl.textContent = text;
    }
  }

  /**
   * 获取当前进度文本
   * @returns {string}
   */
  getText() {
    return this.text;
  }

  /**
   * 更新进度条显示
   */
  updateBar() {
    const inner = this.element.querySelector('.progress-bar-inner');
    if (inner) {
      const percentage = (this.value / this.max) * 100;
      inner.style.width = `${percentage}%`;
    }

    const textEl = this.element.querySelector('.progress-bar-text');
    if (textEl && this.options.showText && !this.text) {
      textEl.textContent = `${Math.round((this.value / this.max) * 100)}%`;
    }
  }

  /**
   * 显示进度条
   */
  show() {
    if (!this.element) return;
    this.element.style.display = 'block';
    this.isVisible = true;
  }

  /**
   * 隐藏进度条
   */
  hide() {
    if (!this.element) return;
    this.element.style.display = 'none';
    this.isVisible = false;
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
   * 重置进度条
   */
  reset() {
    this.value = 0;
    this.text = '';
    this.updateBar();
    const textEl = this.element.querySelector('.progress-bar-text');
    if (textEl) {
      textEl.textContent = '';
    }
  }

  /**
   * 完成进度条
   */
  complete() {
    this.setValue(100);
    if (this.options.onComplete) {
      this.options.onComplete();
    }
  }
}

export default ProgressBar;

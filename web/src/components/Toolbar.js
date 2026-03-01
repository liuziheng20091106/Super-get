/**
 * Toolbar - 工具栏组件
 * 提供绑定按钮点击事件、按钮启用/禁用状态管理功能
 */
class Toolbar {
  /**
   * 初始化工具栏
   * @param {string} id - 工具栏元素ID
   * @param {Object} options - 配置选项
   */
  constructor(id, options = {}) {
    this.id = id;
    this.element = document.getElementById(id);
    this.options = {
      onButtonClick: options.onButtonClick || null,
    };
    this.buttons = new Map();
    this.init();
  }

  /**
   * 初始化按钮事件
   */
  init() {
    if (!this.element) return;

    const buttonElements = this.element.querySelectorAll('[data-button-id]');
    buttonElements.forEach((btn) => {
      const buttonId = btn.dataset.buttonId;
      this.buttons.set(buttonId, {
        element: btn,
        disabled: btn.disabled || btn.classList.contains('disabled'),
      });

      btn.addEventListener('click', (e) => {
        if (!this.buttons.get(buttonId).disabled) {
          if (this.options.onButtonClick) {
            this.options.onButtonClick(buttonId, e);
          }
        }
      });
    });
  }

  /**
   * 绑定按钮点击事件
   * @param {string} buttonId - 按钮ID
   * @param {Function} handler - 点击处理函数
   */
  onClick(buttonId, handler) {
    const button = this.buttons.get(buttonId);
    if (button && button.element) {
      button.element.addEventListener('click', handler);
    }
  }

  /**
   * 设置按钮启用/禁用状态
   * @param {string} buttonId - 按钮ID
   * @param {boolean} disabled - 是否禁用
   */
  setDisabled(buttonId, disabled) {
    const button = this.buttons.get(buttonId);
    if (button) {
      button.disabled = disabled;
      if (disabled) {
        button.element.setAttribute('disabled', 'disabled');
        button.element.classList.add('disabled');
      } else {
        button.element.removeAttribute('disabled');
        button.element.classList.remove('disabled');
      }
    }
  }

  /**
   * 启用按钮
   * @param {string} buttonId - 按钮ID
   */
  enable(buttonId) {
    this.setDisabled(buttonId, false);
  }

  /**
   * 禁用按钮
   * @param {string} buttonId - 按钮ID
   */
  disable(buttonId) {
    this.setDisabled(buttonId, true);
  }

  /**
   * 检查按钮是否禁用
   * @param {string} buttonId - 按钮ID
   * @returns {boolean}
   */
  isDisabled(buttonId) {
    const button = this.buttons.get(buttonId);
    return button ? button.disabled : true;
  }

  /**
   * 批量设置按钮状态
   * @param {Object} states - 按钮状态对象 {buttonId: disabled}
   */
  setStates(states) {
    Object.keys(states).forEach((buttonId) => {
      this.setDisabled(buttonId, states[buttonId]);
    });
  }

  /**
   * 批量禁用按钮
   * @param {Array} buttonIds - 按钮ID数组
   */
  disableAll(buttonIds) {
    buttonIds.forEach((buttonId) => {
      this.disable(buttonId);
    });
  }

  /**
   * 批量启用按钮
   * @param {Array} buttonIds - 按钮ID数组
   */
  enableAll(buttonIds) {
    buttonIds.forEach((buttonId) => {
      this.enable(buttonId);
    });
  }

  /**
   * 获取按钮元素
   * @param {string} buttonId - 按钮ID
   * @returns {HTMLElement|null}
   */
  getButton(buttonId) {
    const button = this.buttons.get(buttonId);
    return button ? button.element : null;
  }

  /**
   * 注册新按钮
   * @param {string} buttonId - 按钮ID
   * @param {HTMLElement} element - 按钮元素
   */
  registerButton(buttonId, element) {
    this.buttons.set(buttonId, {
      element: element,
      disabled: element.disabled || element.classList.contains('disabled'),
    });

    element.addEventListener('click', (e) => {
      if (!this.buttons.get(buttonId).disabled) {
        if (this.options.onButtonClick) {
          this.options.onButtonClick(buttonId, e);
        }
      }
    });
  }

  /**
   * 显示按钮
   * @param {string} buttonId - 按钮ID
   */
  show(buttonId) {
    const button = this.buttons.get(buttonId);
    if (button && button.element) {
      button.element.style.display = '';
    }
  }

  /**
   * 隐藏按钮
   * @param {string} buttonId - 按钮ID
   */
  hide(buttonId) {
    const button = this.buttons.get(buttonId);
    if (button && button.element) {
      button.element.style.display = 'none';
    }
  }

  /**
   * 获取所有按钮ID
   * @returns {Array}
   */
  getAllButtonIds() {
    return Array.from(this.buttons.keys());
  }
}

export default Toolbar;

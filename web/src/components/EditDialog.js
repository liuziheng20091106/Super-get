/**
 * EditDialog - 编辑对话框组件
 * 提供显示编辑表单、确认/取消事件功能
 */
class EditDialog {
  /**
   * 初始化编辑对话框
   * @param {string} id - 对话框元素ID
   * @param {Object} options - 配置选项
   */
  constructor(id, options = {}) {
    this.id = id;
    this.element = document.getElementById(id);
    this.options = {
      title: options.title || '编辑',
      onConfirm: options.onConfirm || null,
      onCancel: options.onCancel || null,
      onShow: options.onShow || null,
      onHide: options.onHide || null,
      fields: options.fields || [],
      validate: options.validate || null,
    };
    this.form = null;
    this.data = null;
    this.isVisible = false;
    this.init();
  }

  /**
   * 初始化对话框结构
   */
  init() {
    if (!this.element) return;

    this.dialog = this.element.querySelector('.edit-dialog-content');
    if (!this.dialog) {
      this.dialog = this.element;
    }

    this.titleEl = this.dialog.querySelector('.edit-dialog-title');
    this.formContainer = this.dialog.querySelector('.edit-dialog-form');
    this.confirmBtn = this.dialog.querySelector('.edit-dialog-confirm');
    this.cancelBtn = this.dialog.querySelector('.edit-dialog-cancel');
    this.closeBtn = this.dialog.querySelector('.edit-dialog-close');

    this.setupEvents();
  }

  /**
   * 设置事件监听
   */
  setupEvents() {
    if (this.confirmBtn) {
      this.confirmBtn.addEventListener('click', () => {
        this.handleConfirm();
      });
    }

    if (this.cancelBtn) {
      this.cancelBtn.addEventListener('click', () => {
        this.handleCancel();
      });
    }

    if (this.closeBtn) {
      this.closeBtn.addEventListener('click', () => {
        this.hide();
      });
    }

    const overlay = this.element.querySelector('.modal-overlay');
    if (overlay) {
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
          this.hide();
        }
      });
    }

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.isVisible) {
        this.hide();
      }
      if (e.key === 'Enter' && this.isVisible && e.ctrlKey) {
        this.handleConfirm();
      }
    });
  }

  /**
   * 显示编辑对话框
   * @param {Object} data - 要编辑的数据
   */
  show(data = {}) {
    if (!this.element) return;

    this.data = data;
    this.renderForm(data);
    this.element.style.display = 'flex';
    this.isVisible = true;

    if (this.options.onShow) {
      this.options.onShow(data);
    }

    const firstInput = this.formContainer?.querySelector('input, select, textarea');
    if (firstInput) {
      setTimeout(() => firstInput.focus(), 100);
    }
  }

  /**
   * 隐藏对话框
   */
  hide() {
    if (!this.element) return;

    this.element.style.display = 'none';
    this.isVisible = false;
    this.data = null;

    if (this.options.onHide) {
      this.options.onHide();
    }
  }

  /**
   * 渲染表单
   * @param {Object} data - 表单数据
   */
  renderForm(data) {
    if (!this.formContainer) return;

    if (this.options.fields.length === 0) {
      this.formContainer.innerHTML = '<p>未配置表单字段</p>';
      return;
    }

    this.formContainer.innerHTML = '';
    this.form = document.createElement('form');
    this.form.className = 'edit-form';

    this.options.fields.forEach((field) => {
      const fieldWrapper = document.createElement('div');
      fieldWrapper.className = 'form-field';

      const label = document.createElement('label');
      label.textContent = field.label || field.name;
      label.htmlFor = field.name;
      fieldWrapper.appendChild(label);

      let input;
      switch (field.type) {
        case 'select':
          input = document.createElement('select');
          input.name = field.name;
          input.id = field.name;
          if (field.options) {
            field.options.forEach((opt) => {
              const option = document.createElement('option');
              option.value = opt.value;
              option.textContent = opt.label;
              if (data[field.name] === opt.value) {
                option.selected = true;
              }
              input.appendChild(option);
            });
          }
          break;
        case 'textarea':
          input = document.createElement('textarea');
          input.name = field.name;
          input.id = field.name;
          input.value = data[field.name] || '';
          if (field.rows) input.rows = field.rows;
          break;
        case 'checkbox':
          input = document.createElement('input');
          input.type = 'checkbox';
          input.name = field.name;
          input.id = field.name;
          input.checked = data[field.name] || false;
          break;
        default:
          input = document.createElement('input');
          input.type = field.type || 'text';
          input.name = field.name;
          input.id = field.name;
          input.value = data[field.name] || '';
      }

      if (field.placeholder) {
        input.placeholder = field.placeholder;
      }
      if (field.disabled) {
        input.disabled = true;
      }
      if (field.required) {
        input.required = true;
      }

      fieldWrapper.appendChild(input);
      this.form.appendChild(fieldWrapper);
    });

    this.formContainer.appendChild(this.form);
  }

  /**
   * 处理确认事件
   */
  handleConfirm() {
    const formData = this.getFormData();

    if (this.options.validate) {
      const errors = this.options.validate(formData);
      if (errors && errors.length > 0) {
        this.showErrors(errors);
        return;
      }
    }

    if (this.options.onConfirm) {
      this.options.onConfirm(formData, this.data);
    }

    this.hide();
  }

  /**
   * 处理取消事件
   */
  handleCancel() {
    if (this.options.onCancel) {
      this.options.onCancel(this.data);
    }
    this.hide();
  }

  /**
   * 获取表单数据
   * @returns {Object}
   */
  getFormData() {
    if (!this.form) return {};

    const formData = new FormData(this.form);
    const data = {};

    for (const [key, value] of formData.entries()) {
      data[key] = value;
    }

    const checkboxes = this.form.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach((checkbox) => {
      data[checkbox.name] = checkbox.checked;
    });

    return data;
  }

  /**
   * 设置表单数据
   * @param {Object} data - 表单数据
   */
  setFormData(data) {
    if (!this.form) return;

    Object.keys(data).forEach((key) => {
      const input = this.form.querySelector(`[name="${key}"]`);
      if (input) {
        if (input.type === 'checkbox') {
          input.checked = data[key];
        } else {
          input.value = data[key];
        }
      }
    });
  }

  /**
   * 显示错误信息
   * @param {Array} errors - 错误数组
   */
  showErrors(errors) {
    const errorContainer = this.formContainer.querySelector('.form-errors');
    if (errorContainer) {
      errorContainer.remove();
    }

    const newErrorContainer = document.createElement('div');
    newErrorContainer.className = 'form-errors';
    newErrorContainer.innerHTML = errors.map((e) => `<div class="error-message">${e}</div>`).join('');
    this.formContainer.insertBefore(newErrorContainer, this.form);
  }

  /**
   * 清空表单
   */
  clearForm() {
    if (this.form) {
      this.form.reset();
    }
  }

  /**
   * 设置标题
   * @param {string} title - 标题
   */
  setTitle(title) {
    if (this.titleEl) {
      this.titleEl.textContent = title;
    }
  }

  /**
   * 获取标题
   * @returns {string}
   */
  getTitle() {
    return this.titleEl ? this.titleEl.textContent : '';
  }

  /**
   * 设置按钮文本
   * @param {string} confirmText - 确认按钮文本
   * @param {string} cancelText - 取消按钮文本
   */
  setButtonText(confirmText, cancelText) {
    if (this.confirmBtn) {
      this.confirmBtn.textContent = confirmText || '确认';
    }
    if (this.cancelBtn) {
      this.cancelBtn.textContent = cancelText || '取消';
    }
  }
}

export default EditDialog;

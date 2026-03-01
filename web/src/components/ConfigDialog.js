/**
 * ConfigDialog - 配置对话框组件
 * 提供加载配置、保存配置功能
 */
class ConfigDialog {
  /**
   * 初始化配置对话框
   * @param {string} id - 对话框元素ID
   * @param {Object} options - 配置选项
   */
  constructor(id, options = {}) {
    this.id = id;
    this.element = document.getElementById(id);
    this.options = {
      title: options.title || '配置',
      onLoad: options.onLoad || null,
      onSave: options.onSave || null,
      onShow: options.onShow || null,
      onHide: options.onHide || null,
      sections: options.sections || [],
      validate: options.validate || null,
    };
    this.config = {};
    this.isVisible = false;
    this.isDirty = false;
    this.init();
  }

  /**
   * 初始化对话框结构
   */
  init() {
    if (!this.element) return;

    this.dialog = this.element.querySelector('.config-dialog-content');
    if (!this.dialog) {
      this.dialog = this.element;
    }

    this.titleEl = this.dialog.querySelector('.config-dialog-title');
    this.formContainer = this.dialog.querySelector('.config-dialog-form');
    this.saveBtn = this.dialog.querySelector('.config-dialog-save');
    this.cancelBtn = this.dialog.querySelector('.config-dialog-cancel');
    this.resetBtn = this.dialog.querySelector('.config-dialog-reset');
    this.closeBtn = this.dialog.querySelector('.config-dialog-close');

    this.setupEvents();
  }

  /**
   * 设置事件监听
   */
  setupEvents() {
    if (this.saveBtn) {
      this.saveBtn.addEventListener('click', () => {
        this.handleSave();
      });
    }

    if (this.cancelBtn) {
      this.cancelBtn.addEventListener('click', () => {
        this.handleCancel();
      });
    }

    if (this.resetBtn) {
      this.resetBtn.addEventListener('click', () => {
        this.handleReset();
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
      if (e.key === 's' && (e.ctrlKey || e.metaKey) && this.isVisible) {
        e.preventDefault();
        this.handleSave();
      }
    });
  }

  /**
   * 显示配置对话框
   */
  async show() {
    if (!this.element) return;

    await this.loadConfig();

    this.renderForm();
    this.element.style.display = 'flex';
    this.isVisible = true;
    this.isDirty = false;

    if (this.options.onShow) {
      this.options.onShow(this.config);
    }
  }

  /**
   * 隐藏对话框
   */
  hide() {
    if (!this.element) return;

    if (this.isDirty) {
      const confirmed = confirm('有未保存的更改，确定要关闭吗？');
      if (!confirmed) return;
    }

    this.element.style.display = 'none';
    this.isVisible = false;

    if (this.options.onHide) {
      this.options.onHide();
    }
  }

  /**
   * 加载配置
   */
  async loadConfig() {
    if (this.options.onLoad) {
      try {
        this.config = await this.options.onLoad();
      } catch (error) {
        console.error('加载配置失败:', error);
        this.config = this.getDefaultConfig();
      }
    } else {
      this.config = this.getDefaultConfig();
    }
  }

  /**
   * 获取默认配置
   * @returns {Object}
   */
  getDefaultConfig() {
    const defaultConfig = {};
    this.options.sections.forEach((section) => {
      if (section.fields) {
        section.fields.forEach((field) => {
          defaultConfig[field.name] = field.defaultValue !== undefined ? field.defaultValue : '';
        });
      }
    });
    return defaultConfig;
  }

  /**
   * 渲染表单
   */
  renderForm() {
    if (!this.formContainer) return;

    this.formContainer.innerHTML = '';
    this.form = document.createElement('form');
    this.form.className = 'config-form';

    this.options.sections.forEach((section) => {
      const sectionEl = document.createElement('div');
      sectionEl.className = 'config-section';

      if (section.title) {
        const sectionTitle = document.createElement('div');
        sectionTitle.className = 'config-section-title';
        sectionTitle.textContent = section.title;
        sectionEl.appendChild(sectionTitle);
      }

      if (section.description) {
        const sectionDesc = document.createElement('div');
        sectionDesc.className = 'config-section-description';
        sectionDesc.textContent = section.description;
        sectionEl.appendChild(sectionDesc);
      }

      const fieldsContainer = document.createElement('div');
      fieldsContainer.className = 'config-fields';

      if (section.fields) {
        section.fields.forEach((field) => {
          const fieldWrapper = this.createFieldElement(field);
          fieldsContainer.appendChild(fieldWrapper);
        });
      }

      sectionEl.appendChild(fieldsContainer);
      this.form.appendChild(sectionEl);
    });

    this.formContainer.appendChild(this.form);
  }

  /**
   * 创建字段元素
   * @param {Object} field - 字段配置
   * @returns {HTMLElement}
   */
  createFieldElement(field) {
    const fieldWrapper = document.createElement('div');
    fieldWrapper.className = 'config-field';

    const label = document.createElement('label');
    label.textContent = field.label || field.name;
    label.htmlFor = field.name;
    fieldWrapper.appendChild(label);

    let input;
    const value = this.config[field.name] !== undefined ? this.config[field.name] : field.defaultValue;

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
            if (value === opt.value) {
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
        input.value = value || '';
        if (field.rows) input.rows = field.rows;
        break;
      case 'checkbox':
        input = document.createElement('input');
        input.type = 'checkbox';
        input.name = field.name;
        input.id = field.name;
        input.checked = value || false;
        break;
      case 'range':
        input = document.createElement('div');
        input.className = 'range-input-wrapper';
        const rangeInput = document.createElement('input');
        rangeInput.type = 'range';
        rangeInput.name = field.name;
        rangeInput.id = field.name;
        rangeInput.value = value || field.min || 0;
        rangeInput.min = field.min || 0;
        rangeInput.max = field.max || 100;
        rangeInput.step = field.step || 1;
        const rangeValue = document.createElement('span');
        rangeValue.className = 'range-value';
        rangeValue.textContent = rangeInput.value;
        rangeInput.addEventListener('input', () => {
          rangeValue.textContent = rangeInput.value;
          this.markDirty();
        });
        input.appendChild(rangeInput);
        input.appendChild(rangeValue);
        break;
      default:
        input = document.createElement('input');
        input.type = field.type || 'text';
        input.name = field.name;
        input.id = field.name;
        input.value = value || '';
    }

    if (field.type !== 'range') {
      if (field.placeholder) {
        input.placeholder = field.placeholder;
      }
      if (field.disabled) {
        input.disabled = true;
      }
      if (field.required) {
        input.required = true;
      }

      input.addEventListener('change', () => {
        this.markDirty();
      });
    }

    fieldWrapper.appendChild(input);

    if (field.helpText) {
      const helpText = document.createElement('div');
      helpText.className = 'config-field-help';
      helpText.textContent = field.helpText;
      fieldWrapper.appendChild(helpText);
    }

    return fieldWrapper;
  }

  /**
   * 标记为已修改
   */
  markDirty() {
    this.isDirty = true;
    if (this.saveBtn) {
      this.saveBtn.removeAttribute('disabled');
    }
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
   * 处理保存
   */
  async handleSave() {
    const formData = this.getFormData();

    if (this.options.validate) {
      const errors = this.options.validate(formData);
      if (errors && errors.length > 0) {
        this.showErrors(errors);
        return;
      }
    }

    if (this.options.onSave) {
      try {
        await this.options.onSave(formData);
        this.config = formData;
        this.isDirty = false;
        this.hide();
      } catch (error) {
        console.error('保存配置失败:', error);
        alert('保存配置失败，请重试');
      }
    }
  }

  /**
   * 处理取消
   */
  handleCancel() {
    this.hide();
  }

  /**
   * 处理重置
   */
  async handleReset() {
    const confirmed = confirm('确定要重置为默认配置吗？');
    if (!confirmed) return;

    this.config = this.getDefaultConfig();
    this.renderForm();
    this.markDirty();
  }

  /**
   * 显示错误信息
   * @param {Array} errors - 错误数组
   */
  showErrors(errors) {
    const errorContainer = this.formContainer.querySelector('.config-errors');
    if (errorContainer) {
      errorContainer.remove();
    }

    const newErrorContainer = document.createElement('div');
    newErrorContainer.className = 'config-errors';
    newErrorContainer.innerHTML = errors.map((e) => `<div class="error-message">${e}</div>`).join('');
    this.formContainer.insertBefore(newErrorContainer, this.form);
  }

  /**
   * 获取当前配置
   * @returns {Object}
   */
  getConfig() {
    return this.config;
  }

  /**
   * 设置配置
   * @param {Object} config - 配置对象
   */
  setConfig(config) {
    this.config = config;
    if (this.form) {
      Object.keys(config).forEach((key) => {
        const input = this.form.querySelector(`[name="${key}"]`);
        if (input) {
          if (input.type === 'checkbox') {
            input.checked = config[key];
          } else {
            input.value = config[key];
          }
        }
      });
    }
  }

  /**
   * 检查是否有未保存的更改
   * @returns {boolean}
   */
  hasUnsavedChanges() {
    return this.isDirty;
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
   * 添加配置区块
   * @param {Object} section - 区块配置
   */
  addSection(section) {
    this.options.sections.push(section);
  }

  /**
   * 移除配置区块
   * @param {string} sectionTitle - 区块标题
   */
  removeSection(sectionTitle) {
    const index = this.options.sections.findIndex((s) => s.title === sectionTitle);
    if (index !== -1) {
      this.options.sections.splice(index, 1);
    }
  }
}

export default ConfigDialog;

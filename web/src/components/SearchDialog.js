/**
 * SearchDialog - 搜索对话框组件
 * 提供搜索输入和执行、渲染搜索结果、结果点击事件功能
 */
class SearchDialog {
  /**
   * 初始化搜索对话框
   * @param {string} id - 对话框元素ID
   * @param {Object} options - 配置选项
   */
  constructor(id, options = {}) {
    this.id = id;
    this.element = document.getElementById(id);
    this.options = {
      onSearch: options.onSearch || null,
      onResultClick: options.onResultClick || null,
      placeholder: options.placeholder || '搜索...',
      minChars: options.minChars || 1,
      debounce: options.debounce || 300,
      resultTemplate: options.resultTemplate || null,
      maxResults: options.maxResults || 50,
    };
    this.results = [];
    this.selectedIndex = -1;
    this.searchTimer = null;
    this.init();
  }

  /**
   * 初始化事件监听
   */
  init() {
    if (!this.element) return;

    this.searchInput = this.element.querySelector('.search-input');
    this.resultsContainer = this.element.querySelector('.search-results');
    this.clearButton = this.element.querySelector('.search-clear');

    if (this.searchInput) {
      this.searchInput.placeholder = this.options.placeholder;

      this.searchInput.addEventListener('input', (e) => {
        this.handleInput(e.target.value);
      });

      this.searchInput.addEventListener('keydown', (e) => {
        this.handleKeydown(e);
      });
    }

    if (this.clearButton) {
      this.clearButton.addEventListener('click', () => {
        this.clear();
      });
    }

    document.addEventListener('click', (e) => {
      if (this.element && !this.element.contains(e.target)) {
        this.hideResults();
      }
    });
  }

  /**
   * 处理输入事件
   * @param {string} value - 输入值
   */
  handleInput(value) {
    if (this.searchTimer) {
      clearTimeout(this.searchTimer);
    }

    if (value.length >= this.options.minChars) {
      this.searchTimer = setTimeout(() => {
        this.executeSearch(value);
      }, this.options.debounce);
    } else if (value.length === 0) {
      this.clear();
    } else {
      this.hideResults();
    }
  }

  /**
   * 处理键盘事件
   * @param {KeyboardEvent} e - 键盘事件
   */
  handleKeydown(e) {
    if (!this.results.length) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        this.selectNext();
        break;
      case 'ArrowUp':
        e.preventDefault();
        this.selectPrev();
        break;
      case 'Enter':
        e.preventDefault();
        this.confirmSelection();
        break;
      case 'Escape':
        this.hideResults();
        break;
    }
  }

  /**
   * 执行搜索
   * @param {string} query - 搜索关键词
   */
  executeSearch(query) {
    if (this.options.onSearch) {
      this.options.onSearch(query, (results) => {
        this.displayResults(results.slice(0, this.options.maxResults));
      });
    }
  }

  /**
   * 渲染搜索结果
   * @param {Array} results - 搜索结果数组
   */
  displayResults(results) {
    this.results = results;
    this.selectedIndex = -1;

    if (!this.resultsContainer) return;

    this.resultsContainer.innerHTML = '';

    if (results.length === 0) {
      this.resultsContainer.innerHTML = '<div class="search-no-results">未找到结果</div>';
      this.showResults();
      return;
    }

    results.forEach((result, index) => {
      const item = this.createResultItem(result, index);
      this.resultsContainer.appendChild(item);
    });

    this.showResults();
  }

  /**
   * 创建结果项
   * @param {Object} result - 结果数据
   * @param {number} index - 索引
   * @returns {HTMLElement}
   */
  createResultItem(result, index) {
    let item;

    if (this.options.resultTemplate && typeof this.options.resultTemplate === 'function') {
      item = this.options.resultTemplate(result, index);
    } else {
      item = document.createElement('div');
      item.className = 'search-result-item';
      item.innerHTML = `
        <div class="search-result-title">${result.title || result.name || '未命名'}</div>
        <div class="search-result-content">${result.content || result.description || ''}</div>
      `;
    }

    item.dataset.index = index;

    item.addEventListener('click', () => {
      this.selectedIndex = index;
      if (this.options.onResultClick) {
        this.options.onResultClick(result, index);
      }
    });

    item.addEventListener('mouseenter', () => {
      this.selectedIndex = index;
      this.updateSelection();
    });

    return item;
  }

  /**
   * 显示结果列表
   */
  showResults() {
    if (this.resultsContainer) {
      this.resultsContainer.style.display = 'block';
    }
  }

  /**
   * 隐藏结果列表
   */
  hideResults() {
    if (this.resultsContainer) {
      this.resultsContainer.style.display = 'none';
    }
  }

  /**
   * 选中下一项
   */
  selectNext() {
    if (this.selectedIndex < this.results.length - 1) {
      this.selectedIndex++;
      this.updateSelection();
    }
  }

  /**
   * 选中上一项
   */
  selectPrev() {
    if (this.selectedIndex > 0) {
      this.selectedIndex--;
      this.updateSelection();
    }
  }

  /**
   * 更新选中状态
   */
  updateSelection() {
    const items = this.resultsContainer.querySelectorAll('.search-result-item');
    items.forEach((item, index) => {
      if (index === this.selectedIndex) {
        item.classList.add('selected');
        item.scrollIntoView({ block: 'nearest' });
      } else {
        item.classList.remove('selected');
      }
    });
  }

  /**
   * 确认选择
   */
  confirmSelection() {
    if (this.selectedIndex >= 0 && this.selectedIndex < this.results.length) {
      const result = this.results[this.selectedIndex];
      if (this.options.onResultClick) {
        this.options.onResultClick(result, this.selectedIndex);
      }
    }
  }

  /**
   * 清空搜索
   */
  clear() {
    if (this.searchInput) {
      this.searchInput.value = '';
    }
    this.results = [];
    this.selectedIndex = -1;
    if (this.resultsContainer) {
      this.resultsContainer.innerHTML = '';
    }
    this.hideResults();
  }

  /**
   * 获取搜索输入值
   * @returns {string}
   */
  getValue() {
    return this.searchInput ? this.searchInput.value : '';
  }

  /**
   * 设置搜索输入值
   * @param {string} value - 输入值
   */
  setValue(value) {
    if (this.searchInput) {
      this.searchInput.value = value;
      if (value.length >= this.options.minChars) {
        this.executeSearch(value);
      }
    }
  }

  /**
   * 获取当前选中的结果
   * @returns {Object|null}
   */
  getSelectedResult() {
    if (this.selectedIndex >= 0 && this.selectedIndex < this.results.length) {
      return this.results[this.selectedIndex];
    }
    return null;
  }

  /**
   * 获取所有结果
   * @returns {Array}
   */
  getResults() {
    return this.results;
  }

  /**
   * 聚焦搜索输入
   */
  focus() {
    if (this.searchInput) {
      this.searchInput.focus();
    }
  }

  /**
   * 失去焦点
   */
  blur() {
    if (this.searchInput) {
      this.searchInput.blur();
    }
  }
}

export default SearchDialog;

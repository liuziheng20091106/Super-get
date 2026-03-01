/**
 * Sidebar - 侧边栏组件
 * 提供渲染书籍列表、点击选中事件和右键菜单支持功能
 */
class Sidebar {
  /**
   * 初始化侧边栏
   * @param {string} id - 侧边栏元素ID
   * @param {Object} options - 配置选项
   */
  constructor(id, options = {}) {
    this.id = id;
    this.element = document.getElementById(id);
    this.options = {
      onSelect: options.onSelect || null,
      onContextMenu: options.onContextMenu || null,
      itemTemplate: options.itemTemplate || null,
      selectedClass: options.selectedClass || 'selected',
    };
    this.items = [];
    this.selectedIndex = -1;
    this.contextMenu = null;
    this.init();
  }

  /**
   * 初始化事件监听
   */
  init() {
    if (!this.element) return;

    this.listContainer = this.element.querySelector('.sidebar-list');
    if (!this.listContainer) {
      this.listContainer = document.createElement('div');
      this.listContainer.className = 'sidebar-list';
      this.element.appendChild(this.listContainer);
    }
  }

  /**
   * 渲染书籍列表
   * @param {Array} books - 书籍数据数组
   */
  render(books) {
    this.items = books;
    this.listContainer.innerHTML = '';

    books.forEach((book, index) => {
      const item = this.createItem(book, index);
      this.listContainer.appendChild(item);
    });
  }

  /**
   * 创建列表项
   * @param {Object} book - 书籍数据
   * @param {number} index - 索引
   * @returns {HTMLElement}
   */
  createItem(book, index) {
    let item;

    if (this.options.itemTemplate && typeof this.options.itemTemplate === 'function') {
      item = this.options.itemTemplate(book, index);
    } else {
      item = document.createElement('div');
      item.className = 'sidebar-item';
      item.innerHTML = `
        <div class="sidebar-item-icon">📖</div>
        <div class="sidebar-item-content">
          <div class="sidebar-item-title">${book.title || book.name || '未命名'}</div>
          <div class="sidebar-item-subtitle">${book.author || ''}</div>
        </div>
      `;
    }

    item.dataset.index = index;
    item.dataset.id = book.id || index;

    item.addEventListener('click', (e) => {
      this.select(index);
      if (this.options.onSelect) {
        this.options.onSelect(book, index);
      }
    });

    item.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      this.select(index);
      if (this.options.onContextMenu) {
        this.options.onContextMenu(e, book, index);
      }
    });

    return item;
  }

  /**
   * 选中指定项
   * @param {number} index - 要选中的索引
   */
  select(index) {
    const items = this.listContainer.querySelectorAll('.sidebar-item');
    items.forEach((item, i) => {
      if (i === index) {
        item.classList.add(this.options.selectedClass);
      } else {
        item.classList.remove(this.options.selectedClass);
      }
    });
    this.selectedIndex = index;
  }

  /**
   * 获取选中的项
   * @returns {Object|null}
   */
  getSelected() {
    if (this.selectedIndex >= 0 && this.selectedIndex < this.items.length) {
      return this.items[this.selectedIndex];
    }
    return null;
  }

  /**
   * 获取选中的索引
   * @returns {number}
   */
  getSelectedIndex() {
    return this.selectedIndex;
  }

  /**
   * 取消选中
   */
  deselect() {
    const items = this.listContainer.querySelectorAll('.sidebar-item');
    items.forEach((item) => {
      item.classList.remove(this.options.selectedClass);
    });
    this.selectedIndex = -1;
  }

  /**
   * 绑定右键菜单
   * @param {ContextMenu} contextMenu - 右键菜单实例
   */
  setContextMenu(contextMenu) {
    this.contextMenu = contextMenu;
  }

  /**
   * 添加新项
   * @param {Object} book - 书籍数据
   */
  addItem(book) {
    const index = this.items.length;
    this.items.push(book);
    const item = this.createItem(book, index);
    this.listContainer.appendChild(item);
  }

  /**
   * 移除指定项
   * @param {number} index - 要移除的索引
   */
  removeItem(index) {
    if (index >= 0 && index < this.items.length) {
      this.items.splice(index, 1);
      this.render(this.items);
    }
  }

  /**
   * 清空列表
   */
  clear() {
    this.items = [];
    this.listContainer.innerHTML = '';
    this.selectedIndex = -1;
  }

  /**
   * 获取所有项
   * @returns {Array}
   */
  getItems() {
    return this.items;
  }

  /**
   * 获取指定索引的项
   * @param {number} index - 索引
   * @returns {Object|null}
   */
  getItem(index) {
    if (index >= 0 && index < this.items.length) {
      return this.items[index];
    }
    return null;
  }
}

export default Sidebar;

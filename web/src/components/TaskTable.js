/**
 * TaskTable - 任务表格组件
 * 提供渲染任务列表、行选中事件、右键菜单支持、多选支持功能
 */
class TaskTable {
  /**
   * 初始化任务表格
   * @param {string} id - 表格元素ID
   * @param {Object} options - 配置选项
   */
  constructor(id, options = {}) {
    this.id = id;
    this.element = document.getElementById(id);
    this.options = {
      columns: options.columns || [],
      onRowClick: options.onRowClick || null,
      onRowSelect: options.onRowSelect || null,
      onContextMenu: options.onContextMenu || null,
      multiSelect: options.multiSelect !== false,
      selectable: options.selectable !== false,
      rowTemplate: options.rowTemplate || null,
      selectedClass: options.selectedClass || 'selected',
    };
    this.data = [];
    this.selectedRows = new Set();
    this.contextMenu = null;
    this.init();
  }

  /**
   * 初始化表格结构
   */
  init() {
    if (!this.element) return;

    this.table = this.element.querySelector('table');
    if (!this.table) {
      this.table = document.createElement('table');
      this.element.appendChild(this.table);
    }

    this.thead = this.table.querySelector('thead');
    if (!this.thead) {
      this.thead = document.createElement('thead');
      this.table.appendChild(this.thead);
    }

    this.tbody = this.table.querySelector('tbody');
    if (!this.tbody) {
      this.tbody = document.createElement('tbody');
      this.table.appendChild(this.tbody);
    }

    this.renderHeader();
  }

  /**
   * 渲染表头
   */
  renderHeader() {
    if (this.options.columns.length === 0) return;

    this.thead.innerHTML = '';
    const tr = document.createElement('tr');

    if (this.options.multiSelect) {
      const th = document.createElement('th');
      th.className = 'checkbox-col';
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.addEventListener('change', (e) => {
        if (e.target.checked) {
          this.selectAll();
        } else {
          this.deselectAll();
        }
      });
      th.appendChild(checkbox);
      tr.appendChild(th);
    }

    this.options.columns.forEach((col) => {
      const th = document.createElement('th');
      th.textContent = col.title || col.key;
      th.style.width = col.width || 'auto';
      tr.appendChild(th);
    });

    this.thead.appendChild(tr);
  }

  /**
   * 渲染任务列表
   * @param {Array} tasks - 任务数据数组
   */
  render(tasks) {
    this.data = tasks;
    this.tbody.innerHTML = '';
    this.selectedRows.clear();

    tasks.forEach((task, index) => {
      const row = this.createRow(task, index);
      this.tbody.appendChild(row);
    });
  }

  /**
   * 创建表格行
   * @param {Object} task - 任务数据
   * @param {number} index - 行索引
   * @returns {HTMLElement}
   */
  createRow(task, index) {
    const tr = document.createElement('tr');
    tr.dataset.index = index;
    tr.dataset.id = task.id || index;

    if (this.options.multiSelect) {
      const td = document.createElement('td');
      td.className = 'checkbox-col';
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.addEventListener('change', (e) => {
        if (e.target.checked) {
          this.selectRow(index, true);
        } else {
          this.deselectRow(index, true);
        }
      });
      checkbox.addEventListener('click', (e) => e.stopPropagation());
      td.appendChild(checkbox);
      tr.appendChild(td);
    }

    if (this.options.rowTemplate && typeof this.options.rowTemplate === 'function') {
      const customContent = this.options.rowTemplate(task, index);
      if (customContent instanceof HTMLElement) {
        const td = document.createElement('td');
        td.appendChild(customContent);
        tr.appendChild(td);
      } else {
        tr.innerHTML += customContent;
      }
    } else {
      this.options.columns.forEach((col) => {
        const td = document.createElement('td');
        td.textContent = task[col.key] || '';
        tr.appendChild(td);
      });
    }

    if (this.options.selectable) {
      tr.addEventListener('click', (e) => {
        if (e.ctrlKey || e.metaKey) {
          if (this.selectedRows.has(index)) {
            this.deselectRow(index, true);
          } else {
            this.selectRow(index, true);
          }
        } else if (this.options.multiSelect && e.shiftKey) {
          this.selectRange(index);
        } else {
          this.selectRow(index, false);
        }

        if (this.options.onRowClick) {
          this.options.onRowClick(task, index);
        }
      });

      tr.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        if (!this.selectedRows.has(index)) {
          this.selectRow(index, false);
        }
        if (this.options.onContextMenu) {
          this.options.onContextMenu(e, task, index);
        }
      });
    }

    return tr;
  }

  /**
   * 选中指定行
   * @param {number} index - 行索引
   * @param {boolean} keepExisting - 是否保留现有选中
   */
  selectRow(index, keepExisting = false) {
    if (!keepExisting) {
      this.deselectAll();
    }

    this.selectedRows.add(index);
    this.updateRowStyle(index, true);

    if (this.options.onRowSelect) {
      this.options.onRowSelect(this.getSelectedData());
    }
  }

  /**
   * 取消选中指定行
   * @param {number} index - 行索引
   * @param {boolean} notify - 是否触发回调
   */
  deselectRow(index, notify = true) {
    this.selectedRows.delete(index);
    this.updateRowStyle(index, false);

    if (notify && this.options.onRowSelect) {
      this.options.onRowSelect(this.getSelectedData());
    }
  }

  /**
   * 选中连续范围
   * @param {number} endIndex - 结束索引
   */
  selectRange(endIndex) {
    if (this.selectedRows.size === 0) {
      this.selectRow(endIndex, false);
      return;
    }

    const lastSelected = Array.from(this.selectedRows).pop();
    const start = Math.min(lastSelected, endIndex);
    const end = Math.max(lastSelected, endIndex);

    for (let i = start; i <= end; i++) {
      this.selectedRows.add(i);
      this.updateRowStyle(i, true);
    }

    if (this.options.onRowSelect) {
      this.options.onRowSelect(this.getSelectedData());
    }
  }

  /**
   * 全选
   */
  selectAll() {
    this.data.forEach((_, index) => {
      this.selectedRows.add(index);
      this.updateRowStyle(index, true);
    });

    if (this.options.onRowSelect) {
      this.options.onRowSelect(this.getSelectedData());
    }
  }

  /**
   * 取消全选
   */
  deselectAll() {
    this.selectedRows.forEach((index) => {
      this.updateRowStyle(index, false);
    });
    this.selectedRows.clear();

    if (this.options.onRowSelect) {
      this.options.onRowSelect(this.getSelectedData());
    }
  }

  /**
   * 更新行样式
   * @param {number} index - 行索引
   * @param {boolean} selected - 是否选中
   */
  updateRowStyle(index, selected) {
    const rows = this.tbody.querySelectorAll('tr');
    if (rows[index]) {
      if (selected) {
        rows[index].classList.add(this.options.selectedClass);
      } else {
        rows[index].classList.remove(this.options.selectedClass);
      }
    }
  }

  /**
   * 获取选中的数据
   * @returns {Array}
   */
  getSelectedData() {
    return Array.from(this.selectedRows).map((index) => this.data[index]);
  }

  /**
   * 获取选中的行索引
   * @returns {Array}
   */
  getSelectedIndices() {
    return Array.from(this.selectedRows);
  }

  /**
   * 是否有选中行
   * @returns {boolean}
   */
  hasSelection() {
    return this.selectedRows.size > 0;
  }

  /**
   * 获取选中数量
   * @returns {number}
   */
  getSelectionCount() {
    return this.selectedRows.size;
  }

  /**
   * 绑定右键菜单
   * @param {ContextMenu} contextMenu - 右键菜单实例
   */
  setContextMenu(contextMenu) {
    this.contextMenu = contextMenu;
  }

  /**
   * 添加新行
   * @param {Object} task - 任务数据
   */
  addRow(task) {
    const index = this.data.length;
    this.data.push(task);
    const row = this.createRow(task, index);
    this.tbody.appendChild(row);
  }

  /**
   * 移除指定行
   * @param {number} index - 行索引
   */
  removeRow(index) {
    if (index >= 0 && index < this.data.length) {
      this.data.splice(index, 1);
      this.render(this.data);
    }
  }

  /**
   * 清空表格
   */
  clear() {
    this.data = [];
    this.selectedRows.clear();
    this.tbody.innerHTML = '';
  }

  /**
   * 获取所有数据
   * @returns {Array}
   */
  getData() {
    return this.data;
  }
}

export default TaskTable;

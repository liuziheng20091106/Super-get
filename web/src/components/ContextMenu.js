/**
 * ContextMenu - 右键菜单组件
 * 提供右键菜单显示、菜单位置定位、菜单项点击事件和点击外部关闭功能
 */
class ContextMenu {
  /**
   * 初始化右键菜单
   * @param {string} id - 菜单元素ID
   * @param {Object} options - 配置选项
   */
  constructor(id, options = {}) {
    this.id = id;
    this.element = document.getElementById(id);
    this.options = {
      onItemClick: options.onItemClick || null,
      onClose: options.onClose || null,
    };
    this.isVisible = false;
    this.menuItems = [];
    this.init();
  }

  /**
   * 初始化事件监听
   */
  init() {
    if (!this.element) return;

    document.addEventListener('click', (e) => {
      if (this.isVisible && !this.element.contains(e.target)) {
        this.hide();
      }
    });

    document.addEventListener('contextmenu', (e) => {
      if (this.isVisible && !this.element.contains(e.target)) {
        this.hide();
      }
    });

    const items = this.element.querySelectorAll('.context-menu-item');
    items.forEach((item, index) => {
      item.addEventListener('click', (e) => {
        e.stopPropagation();
        if (this.options.onItemClick) {
          this.options.onItemClick(index, item.dataset.action);
        }
        this.hide();
      });
    });
  }

  /**
   * 在指定位置显示菜单
   * @param {number} x - X坐标
   * @param {number} y - Y坐标
   * @param {Object} data - 传递给菜单的数据
   */
  show(x, y, data = {}) {
    if (!this.element) return;

    this.data = data;
    let posX = x;
    let posY = y;

    const menuWidth = this.element.offsetWidth || 200;
    const menuHeight = this.element.offsetHeight || 200;
    const windowWidth = window.innerWidth;
    const windowHeight = window.innerHeight;

    if (posX + menuWidth > windowWidth) {
      posX = windowWidth - menuWidth - 10;
    }
    if (posY + menuHeight > windowHeight) {
      posY = windowHeight - menuHeight - 10;
    }

    this.element.style.left = `${posX}px`;
    this.element.style.top = `${posY}px`;
    this.element.style.display = 'block';
    this.isVisible = true;
  }

  /**
   * 隐藏菜单
   */
  hide() {
    if (!this.element) return;
    this.element.style.display = 'none';
    this.isVisible = false;
    if (this.options.onClose) {
      this.options.onClose(this.data);
    }
  }

  /**
   * 设置菜单项
   * @param {Array} items - 菜单项数组 [{label, action, disabled}]
   */
  setItems(items) {
    if (!this.element) return;

    const menuList = this.element.querySelector('.context-menu-list');
    if (!menuList) return;

    menuList.innerHTML = '';
    this.menuItems = items;

    items.forEach((item, index) => {
      const menuItem = document.createElement('div');
      menuItem.className = 'context-menu-item';
      if (item.disabled) {
        menuItem.classList.add('disabled');
      }
      menuItem.dataset.action = item.action;
      menuItem.dataset.index = index;
      menuItem.textContent = item.label;
      menuList.appendChild(menuItem);
    });

    this.init();
  }

  /**
   * 切换显示状态
   */
  toggle() {
    if (this.isVisible) {
      this.hide();
    }
  }

  /**
   * 获取当前菜单数据
   * @returns {Object}
   */
  getData() {
    return this.data || {};
  }
}

export default ContextMenu;

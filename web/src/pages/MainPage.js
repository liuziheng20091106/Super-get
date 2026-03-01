/**
 * MainPage - 页面主逻辑
 * 整合所有组件、实现页面初始化、事件通信、任务操作等功能
 */
class MainPage {
  /**
   * 初始化主页面
   * @param {Object} options - 配置选项
   */
  constructor(options = {}) {
    this.options = options;
    this.currentAlbum = null;
    this.tasks = [];
    this.selectedTaskIndices = new Set();
    this.isProcessing = false;
    this.progressPollingTimer = null;

    this.initComponents();
    this.bindEvents();
    this.initEventBus();
  }

  /**
   * 初始化所有组件
   */
  initComponents() {
    this.sidebar = new Sidebar('sidebar', {
      onSelect: (album, index) => this.onAlbumSelect(album, index),
      onContextMenu: (e, album, index) => this.showAlbumContextMenu(e, album, index),
    });

    this.toolbar = new Toolbar('toolbar');

    this.taskTable = new TaskTable('task-table-container', {
      columns: [
        { key: 'index', title: '序号', width: '60px' },
        { key: 'name', title: '名称' },
        { key: 'parseStatus', title: '解析状态', width: '100px' },
        { key: 'downloadStatus', title: '下载状态', width: '100px' },
        { key: 'addTime', title: '添加时间', width: '150px' },
      ],
      multiSelect: true,
      onRowSelect: (selectedTasks) => this.onTaskSelect(selectedTasks),
      onContextMenu: (e, task, index) => this.showTaskContextMenu(e, task, index),
    });

    this.progressBar = new ProgressBar('progress-container', {
      showText: true,
    });

    this.searchDialog = new SearchDialog('search-dialog', {
      onSearch: (query, callback) => this.handleSearch(query, callback),
      onResultClick: (result) => this.onSearchResultClick(result),
    });

    this.editDialog = new Modal('edit-dialog', {
      onClose: () => this.onEditDialogClose(),
    });

    this.configDialog = new Modal('config-dialog', {
      onClose: () => this.onConfigDialogClose(),
    });

    this.contextMenu = new ContextMenu('context-menu', {
      onItemClick: (index, action) => this.onContextMenuItemClick(index, action),
    });

    this.toastContainer = document.getElementById('toast-container');
  }

  /**
   * 绑定页面元素事件
   */
  bindEvents() {
    this.bindToolbarEvents();
    this.bindAlbumInfoEvents();
    this.bindDialogEvents();
    this.bindKeyboardShortcuts();
  }

  /**
   * 绑定工具栏按钮事件
   */
  bindToolbarEvents() {
    const btnMap = {
      'btn-search': () => this.openSearchDialog(),
      'btn-update-catalog': () => this.updateCatalog(),
      'btn-parse': () => this.parseSelectedTasks(),
      'btn-parse-all': () => this.parseAllTasks(),
      'btn-select-unparsed': () => this.selectUnparsedTasks(),
      'btn-invert-selection': () => this.invertSelection(),
      'btn-download': () => this.downloadSelectedTasks(),
      'btn-download-all': () => this.downloadAllTasks(),
      'btn-parse-download-all': () => this.parseAndDownloadAll(),
      'btn-stop': () => this.stopTask(),
      'btn-delete-selected': () => this.deleteSelectedTasks(),
      'btn-delete-album': () => this.deleteCurrentAlbum(),
      'btn-clear-completed': () => this.clearCompletedTasks(),
    };

    Object.keys(btnMap).forEach((btnId) => {
      const btn = document.getElementById(btnId);
      if (btn) {
        btn.addEventListener('click', btnMap[btnId]);
      }
    });
  }

  /**
   * 绑定书籍信息区事件
   */
  bindAlbumInfoEvents() {
  }

  /**
   * 绑定对话框事件
   */
  bindDialogEvents() {
    const editCancelBtn = document.getElementById('edit-cancel');
    const editConfirmBtn = document.getElementById('edit-confirm');

    if (editCancelBtn) {
      editCancelBtn.addEventListener('click', () => this.editDialog.hide());
    }
    if (editConfirmBtn) {
      editConfirmBtn.addEventListener('click', () => this.confirmEdit());
    }

    const configResetBtn = document.getElementById('config-reset');
    const configCancelBtn = document.getElementById('config-cancel');
    const configSaveBtn = document.getElementById('config-save');

    if (configResetBtn) {
      configResetBtn.addEventListener('click', () => this.resetConfig());
    }
    if (configCancelBtn) {
      configCancelBtn.addEventListener('click', () => this.configDialog.hide());
    }
    if (configSaveBtn) {
      configSaveBtn.addEventListener('click', () => this.saveConfig());
    }

    document.querySelectorAll('.modal-close').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const modal = e.target.closest('.modal');
        if (modal) {
          modal.classList.add('hidden');
        }
      });
    });
  }

  /**
   * 绑定键盘快捷键
   */
  bindKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
      if (e.ctrlKey || e.metaKey) {
        switch (e.key) {
          case 'a':
            e.preventDefault();
            this.taskTable.selectAll();
            break;
          case 'f':
            e.preventDefault();
            this.openSearchDialog();
            break;
        }
      }

      if (e.key === 'Delete') {
        if (this.taskTable.hasSelection()) {
          this.deleteSelectedTasks();
        }
      }

      if (e.key === 'Escape') {
        this.contextMenu.hide();
        this.searchDialog.hide();
        this.editDialog.hide();
        this.configDialog.hide();
      }
    });
  }

  /**
   * 初始化事件总线
   */
  initEventBus() {
    this.eventBus = {
      emit: (event, data) => this.handleEvent(event, data),
      on: (event, handler) => {
        if (!this.handlers) this.handlers = {};
        if (!this.handlers[event]) this.handlers[event] = [];
        this.handlers[event].push(handler);
      },
    };
  }

  /**
   * 处理事件
   * @param {string} event - 事件名称
   * @param {any} data - 事件数据
   */
  handleEvent(event, data) {
    if (this.handlers && this.handlers[event]) {
      this.handlers[event].forEach((handler) => handler(data));
    }

    switch (event) {
      case 'task:update':
        this.updateTaskTable();
        break;
      case 'task:progress':
        this.updateProgress(data);
        break;
      case 'task:complete':
        this.onTaskComplete(data);
        break;
      case 'album:change':
        this.onAlbumChange(data);
        break;
    }
  }

  /**
   * 页面初始化完成
   */
  init() {
    this.updateStatusBar('就绪');
    this.updateToolbarState();
    this.loadInitialData();
  }

  /**
   * 加载初始数据
   */
  async loadInitialData() {
    try {
      const albums = await api.getBookshelf();
      this.sidebar.render(albums);
      this.updateStatusBar(`已加载 ${albums.length} 个专辑`);
    } catch (error) {
      this.showToast('加载书架失败: ' + error.message, 'error');
      this.updateStatusBar('加载失败');
    }
  }

  /**
   * 专辑选择事件处理
   * @param {Object} album - 专辑数据
   * @param {number} index - 索引
   */
  async onAlbumSelect(album, index) {
    this.currentAlbum = album;
    this.updateAlbumInfo(album);

    try {
      const chapters = await api.getChapters(album.id);
      this.tasks = chapters.map((chapter, idx) => ({
        id: chapter.chapterid,
        index: idx + 1,
        name: chapter.title,
        parseStatus: chapter.parsed ? '已解析' : '未解析',
        downloadStatus: chapter.downloaded ? '已完成' : '未下载',
        addTime: chapter.addTime || this.formatDate(new Date()),
        url: chapter.url || '',
        parsed: chapter.parsed || false,
        downloaded: chapter.downloaded || false,
      }));
      this.updateTaskTable();
      this.updateStatusBar(`已加载 ${this.tasks.length} 个任务`);
    } catch (error) {
      this.showToast('加载章节失败: ' + error.message, 'error');
    }
  }

  /**
   * 更新专辑信息显示
   * @param {Object} album - 专辑数据
   */
  updateAlbumInfo(album) {
    const albumName = document.getElementById('album-name');
    const albumId = document.getElementById('album-id');
    const albumArtist = document.getElementById('album-artist');
    const taskCount = document.getElementById('task-count');

    if (albumName) albumName.textContent = `专辑名: ${album.name || album.title || '未命名'}`;
    if (albumId) albumId.textContent = `专辑ID: ${album.id || '-'}`;
    if (albumArtist) albumArtist.textContent = `艺术家: ${album.author || '-'}`;
    if (taskCount) taskCount.textContent = `任务数: ${this.tasks.length}`;
  }

  /**
   * 任务选中事件处理
   * @param {Array} selectedTasks - 选中的任务
   */
  onTaskSelect(selectedTasks) {
    this.selectedTaskIndices = new Set(
      selectedTasks.map((t) => this.tasks.indexOf(t))
    );
    this.updateToolbarState();
  }

  /**
   * 显示专辑右键菜单
   * @param {Event} e - 鼠标事件
   * @param {Object} album - 专辑数据
   * @param {number} index - 索引
   */
  showAlbumContextMenu(e, album, index) {
    const items = [
      { label: '更新目录', action: 'update-catalog' },
      { label: '解析全部', action: 'parse-all' },
      { label: '下载全部', action: 'download-all' },
      { label: '解析并下载', action: 'parse-download-all' },
      { label: '删除专辑', action: 'delete-album' },
    ];
    this.contextMenu.setItems(items);
    this.contextMenu.show(e.pageX, e.pageY, { album, index });
  }

  /**
   * 显示任务右键菜单
   * @param {Event} e - 鼠标事件
   * @param {Object} task - 任务数据
   * @param {number} index - 索引
   */
  showTaskContextMenu(e, task, index) {
    const items = [
      { label: '编辑', action: 'edit', disabled: false },
      { label: '解析', action: 'parse', disabled: task.parsed },
      { label: '下载', action: 'download', disabled: !task.parsed || task.downloaded },
      { label: '重新解析', action: 'reparse' },
      { label: '-' },
      { label: '删除', action: 'delete' },
    ];
    this.contextMenu.setItems(items);
    this.contextMenu.show(e.pageX, e.pageY, { task, index });
  }

  /**
   * 右键菜单项点击事件
   * @param {number} index - 菜单项索引
   * @param {string} action - 操作类型
   */
  async onContextMenuItemClick(index, action) {
    const data = this.contextMenu.getData();

    switch (action) {
      case 'update-catalog':
        this.updateCatalog();
        break;
      case 'parse-all':
        this.parseAllTasks();
        break;
      case 'download-all':
        this.downloadAllTasks();
        break;
      case 'parse-download-all':
        this.parseAndDownloadAll();
        break;
      case 'delete-album':
        this.deleteCurrentAlbum();
        break;
      case 'edit':
        this.openEditDialog(data.task, data.index);
        break;
      case 'parse':
        await this.parseTasks([data.index]);
        break;
      case 'download':
        await this.downloadTasks([data.index]);
        break;
      case 'reparse':
        await this.reparseTask(data.index);
        break;
      case 'delete':
        this.deleteTasks([data.index]);
        break;
    }
  }

  /**
   * 打开搜索对话框
   */
  openSearchDialog() {
    const dialog = document.getElementById('search-dialog');
    if (dialog) {
      dialog.classList.remove('hidden');
      const input = document.getElementById('search-input');
      if (input) {
        input.focus();
      }
    }
  }

  /**
   * 处理搜索请求
   * @param {string} query - 搜索关键词
   * @param {Function} callback - 回调函数
   */
  async handleSearch(query, callback) {
    const statusEl = document.getElementById('search-status');
    if (statusEl) statusEl.textContent = '搜索中...';

    try {
      const results = await api.search(query);
      if (statusEl) statusEl.textContent = `找到 ${results.length} 个结果`;
      callback(results);
    } catch (error) {
      if (statusEl) statusEl.textContent = '搜索失败: ' + error.message;
      callback([]);
    }
  }

  /**
   * 搜索结果点击事件
   * @param {Object} result - 搜索结果
   */
  async onSearchResultClick(result) {
    try {
      await api.addToBookshelf(result.id);
      this.sidebar.addItem(result);
      this.showToast('已添加到书架', 'success');

      const dialog = document.getElementById('search-dialog');
      if (dialog) dialog.classList.add('hidden');
    } catch (error) {
      this.showToast('添加失败: ' + error.message, 'error');
    }
  }

  /**
   * 更新目录
   */
  async updateCatalog() {
    if (!this.currentAlbum) {
      this.showToast('请先选择一个专辑', 'warning');
      return;
    }

    this.setProcessingState(true);
    this.updateProgressBar(0, '正在更新目录...');

    try {
      const chapters = await api.getChapters(this.currentAlbum.id);
      this.tasks = chapters.map((chapter, idx) => ({
        id: chapter.chapterid,
        index: idx + 1,
        name: chapter.title,
        parseStatus: chapter.parsed ? '已解析' : '未解析',
        downloadStatus: chapter.downloaded ? '已完成' : '未下载',
        addTime: chapter.addTime || this.formatDate(new Date()),
        url: chapter.url || '',
        parsed: chapter.parsed || false,
        downloaded: chapter.downloaded || false,
      }));
      this.updateTaskTable();
      this.updateProgressBar(100, '更新完成');
      this.showToast('目录更新成功', 'success');
    } catch (error) {
      this.showToast('更新失败: ' + error.message, 'error');
    } finally {
      this.setProcessingState(false);
      this.updateStatusBar('就绪');
    }
  }

  /**
   * 解析选中的任务
   */
  async parseSelectedTasks() {
    const indices = this.taskTable.getSelectedIndices();
    if (indices.length === 0) {
      this.showToast('请先选择要解析的任务', 'warning');
      return;
    }
    await this.parseTasks(indices);
  }

  /**
   * 解析全部任务
   */
  async parseAllTasks() {
    if (this.tasks.length === 0) {
      this.showToast('没有可解析的任务', 'warning');
      return;
    }
    const indices = this.tasks.map((_, i) => i);
    await this.parseTasks(indices);
  }

  /**
   * 解析指定任务
   * @param {Array} indices - 任务索引数组
   */
  async parseTasks(indices) {
    if (!this.currentAlbum) {
      this.showToast('请先选择一个专辑', 'warning');
      return;
    }

    this.setProcessingState(true);
    const chapterIds = indices.map((i) => this.tasks[i].id);

    try {
      this.updateProgressBar(0, '正在解析...');
      await api.startParse(this.currentAlbum.id, chapterIds);
      this.startProgressPolling('parse');
    } catch (error) {
      this.showToast('解析失败: ' + error.message, 'error');
      this.setProcessingState(false);
    }
  }

  /**
   * 重新解析任务
   * @param {number} index - 任务索引
   */
  async reparseTask(index) {
    const task = this.tasks[index];
    task.parsed = false;
    await this.parseTasks([index]);
  }

  /**
   * 选中未解析的任务
   */
  selectUnparsedTasks() {
    const unparsedIndices = [];
    this.tasks.forEach((task, index) => {
      if (!task.parsed) {
        unparsedIndices.push(index);
      }
    });

    this.taskTable.deselectAll();
    unparsedIndices.forEach((index) => {
      this.taskTable.selectRow(index, true);
    });

    this.showToast(`已选中 ${unparsedIndices.length} 个未解析任务`, 'info');
  }

  /**
   * 反向选择
   */
  invertSelection() {
    this.tasks.forEach((_, index) => {
      if (this.selectedTaskIndices.has(index)) {
        this.taskTable.deselectRow(index, true);
      } else {
        this.taskTable.selectRow(index, true);
      }
    });
  }

  /**
   * 下载选中的任务
   */
  async downloadSelectedTasks() {
    const indices = this.taskTable.getSelectedIndices();
    if (indices.length === 0) {
      this.showToast('请先选择要下载的任务', 'warning');
      return;
    }
    await this.downloadTasks(indices);
  }

  /**
   * 下载全部任务
   */
  async downloadAllTasks() {
    if (this.tasks.length === 0) {
      this.showToast('没有可下载的任务', 'warning');
      return;
    }
    const indices = this.tasks.map((_, i) => i);
    await this.downloadTasks(indices);
  }

  /**
   * 下载指定任务
   * @param {Array} indices - 任务索引数组
   */
  async downloadTasks(indices) {
    if (!this.currentAlbum) {
      this.showToast('请先选择一个专辑', 'warning');
      return;
    }

    const unparsedTasks = indices.filter((i) => !this.tasks[i].parsed);
    if (unparsedTasks.length > 0) {
      this.showToast('请先解析未解析的任务', 'warning');
      return;
    }

    this.setProcessingState(true);
    const chapterIds = indices.map((i) => this.tasks[i].id);

    try {
      this.updateProgressBar(0, '正在下载...');
      await api.addDownload(
        chapterIds.map((id) => ({
          bookId: this.currentAlbum.id,
          chapterId: id,
        }))
      );
      this.startProgressPolling('download');
    } catch (error) {
      this.showToast('下载失败: ' + error.message, 'error');
      this.setProcessingState(false);
    }
  }

  /**
   * 解析并下载全部
   */
  async parseAndDownloadAll() {
    if (!this.currentAlbum) {
      this.showToast('请先选择一个专辑', 'warning');
      return;
    }

    this.setProcessingState(true);
    const chapterIds = this.tasks.map((t) => t.id);

    try {
      this.updateProgressBar(0, '正在解析并下载...');
      await api.startBatch('parse-download', this.currentAlbum.id, chapterIds);
      this.startProgressPolling('parse-download');
    } catch (error) {
      this.showToast('操作失败: ' + error.message, 'error');
      this.setProcessingState(false);
    }
  }

  /**
   * 停止任务
   */
  async stopTask() {
    try {
      await api.stopTask();
      this.stopProgressPolling();
      this.setProcessingState(false);
      this.updateProgressBar(0, '已终止');
      this.showToast('任务已终止', 'info');
    } catch (error) {
      this.showToast('终止失败: ' + error.message, 'error');
    }
  }

  /**
   * 删除选中的任务
   */
  deleteSelectedTasks() {
    const indices = this.taskTable.getSelectedIndices();
    if (indices.length === 0) {
      this.showToast('请先选择要删除的任务', 'warning');
      return;
    }
    this.deleteTasks(indices);
  }

  /**
   * 删除指定任务
   * @param {Array} indices - 任务索引数组
   */
  deleteTasks(indices) {
    const sortedIndices = indices.sort((a, b) => b - a);
    sortedIndices.forEach((index) => {
      this.tasks.splice(index, 1);
    });

    this.updateTaskTable();
    this.updateAlbumInfo(this.currentAlbum);
    this.showToast(`已删除 ${indices.length} 个任务`, 'success');
  }

  /**
   * 删除当前专辑
   */
  async deleteCurrentAlbum() {
    if (!this.currentAlbum) {
      this.showToast('请先选择一个专辑', 'warning');
      return;
    }

    try {
      const index = this.sidebar.getSelectedIndex();
      await api.removeFromBookshelf(this.currentAlbum.id);
      this.sidebar.removeItem(index);
      this.currentAlbum = null;
      this.tasks = [];
      this.updateTaskTable();
      this.updateAlbumInfo({});
      this.showToast('专辑已删除', 'success');
    } catch (error) {
      this.showToast('删除失败: ' + error.message, 'error');
    }
  }

  /**
   * 清空已完成的任务
   */
  clearCompletedTasks() {
    const completedIndices = [];
    this.tasks.forEach((task, index) => {
      if (task.downloaded) {
        completedIndices.push(index);
      }
    });

    if (completedIndices.length === 0) {
      this.showToast('没有已完成的任务', 'warning');
      return;
    }

    this.deleteTasks(completedIndices);
    this.showToast(`已清空 ${completedIndices.length} 个已完成任务`, 'success');
  }

  /**
   * 打开编辑对话框
   * @param {Object} task - 任务数据
   * @param {number} index - 任务索引
   */
  openEditDialog(task, index) {
    this.editingTaskIndex = index;

    const nameInput = document.getElementById('edit-name');
    const urlInput = document.getElementById('edit-url');

    if (nameInput) nameInput.value = task.name;
    if (urlInput) urlInput.value = task.url || '';

    this.editDialog.show();
  }

  /**
   * 确认编辑
   */
  confirmEdit() {
    const nameInput = document.getElementById('edit-name');
    const urlInput = document.getElementById('edit-url');

    if (this.editingTaskIndex !== undefined) {
      const task = this.tasks[this.editingTaskIndex];
      task.name = nameInput.value;
      task.url = urlInput.value;
      this.updateTaskTable();
      this.showToast('修改成功', 'success');
    }

    this.editDialog.hide();
  }

  /**
   * 编辑对话框关闭事件
   */
  onEditDialogClose() {
    this.editingTaskIndex = undefined;
  }

  /**
   * 重置配置
   */
  resetConfig() {
    const defaults = {
      'config-base-url': 'https://i275.com',
      'config-play-url': 'https://i275.com/play/{}.html',
      'config-interval': '0.1',
      'config-timeout': '10',
      'config-retries': '3',
      'config-workers': '32',
      'config-download-timeout': '60',
      'config-download-dir': 'downloads',
    };

    Object.keys(defaults).forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.value = defaults[id];
    });

    this.showToast('已恢复默认配置', 'info');
  }

  /**
   * 保存配置
   */
  async saveConfig() {
    const config = {
      baseUrl: document.getElementById('config-base-url')?.value,
      playUrl: document.getElementById('config-play-url')?.value,
      interval: parseFloat(document.getElementById('config-interval')?.value || '0.1'),
      timeout: parseInt(document.getElementById('config-timeout')?.value || '10'),
      retries: parseInt(document.getElementById('config-retries')?.value || '3'),
      workers: parseInt(document.getElementById('config-workers')?.value || '32'),
      downloadTimeout: parseInt(document.getElementById('config-download-timeout')?.value || '60'),
      downloadDir: document.getElementById('config-download-dir')?.value,
    };

    try {
      localStorage.setItem('app-config', JSON.stringify(config));
      this.configDialog.hide();
      this.showToast('配置已保存', 'success');
    } catch (error) {
      this.showToast('保存失败: ' + error.message, 'error');
    }
  }

  /**
   * 配置对话框关闭事件
   */
  onConfigDialogClose() {
  }

  /**
   * 更新任务表格
   */
  updateTaskTable() {
    this.taskTable.render(this.tasks);
    this.updateToolbarState();
  }

  /**
   * 更新工具栏状态
   */
  updateToolbarState() {
    const hasSelection = this.taskTable.hasSelection();
    const selectionCount = this.taskTable.getSelectionCount();
    const hasTasks = this.tasks.length > 0;
    const isProcessing = this.isProcessing;

    const btnStates = {
      'btn-parse': !isProcessing && hasSelection,
      'btn-parse-all': !isProcessing && hasTasks,
      'btn-select-unparsed': !isProcessing && hasTasks,
      'btn-invert-selection': !isProcessing && hasTasks,
      'btn-download': !isProcessing && hasSelection,
      'btn-download-all': !isProcessing && hasTasks,
      'btn-parse-download-all': !isProcessing && hasTasks,
      'btn-stop': isProcessing,
      'btn-delete-selected': !isProcessing && hasSelection,
      'btn-delete-album': !isProcessing && this.currentAlbum,
      'btn-clear-completed': !isProcessing && hasTasks,
    };

    this.toolbar.setStates(btnStates);
  }

  /**
   * 更新状态栏
   * @param {string} text - 状态文本
   */
  updateStatusBar(text) {
    const statusText = document.getElementById('status-text');
    if (statusText) {
      statusText.textContent = text;
    }
  }

  /**
   * 更新进度条
   * @param {number} value - 进度值
   * @param {string} text - 进度文本
   */
  updateProgressBar(value, text) {
    this.progressBar.setValue(value);
    if (text) {
      this.progressBar.setText(text);
    }
  }

  /**
   * 设置处理状态
   * @param {boolean} processing - 是否正在处理
   */
  setProcessingState(processing) {
    this.isProcessing = processing;
    this.updateToolbarState();
  }

  /**
   * 开始进度轮询
   * @param {string} type - 操作类型
   */
  startProgressPolling(type) {
    this.stopProgressPolling();

    const poll = async () => {
      try {
        const progress = await api.getProgress();
        this.updateProgressBar(progress.percent || 0, progress.message || '处理中...');

        if (progress.completed) {
          this.stopProgressPolling();
          this.setProcessingState(false);
          this.updateProgressBar(100, '完成');
          this.showToast('任务完成', 'success');

          await this.loadInitialData();
          if (this.currentAlbum) {
            await this.onAlbumSelect(this.currentAlbum, this.sidebar.getSelectedIndex());
          }
        }
      } catch (error) {
        console.error('进度获取失败:', error);
      }
    };

    this.progressPollingTimer = setInterval(poll, 1000);
  }

  /**
   * 停止进度轮询
   */
  stopProgressPolling() {
    if (this.progressPollingTimer) {
      clearInterval(this.progressPollingTimer);
      this.progressPollingTimer = null;
    }
  }

  /**
   * 更新进度事件
   * @param {Object} data - 进度数据
   */
  updateProgress(data) {
    this.updateProgressBar(data.percent, data.message);
  }

  /**
   * 任务完成事件
   * @param {Object} data - 任务数据
   */
  onTaskComplete(data) {
    this.showToast('任务完成: ' + data.name, 'success');
  }

  /**
   * 专辑变更事件
   * @param {Object} album - 专辑数据
   */
  onAlbumChange(album) {
    this.currentAlbum = album;
    this.updateAlbumInfo(album);
  }

  /**
   * 显示提示消息
   * @param {string} message - 消息文本
   * @param {string} type - 消息类型 (success, error, warning, info)
   */
  showToast(message, type = 'info') {
    if (!this.toastContainer) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    this.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('show');
    }, 10);

    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => {
        this.toastContainer.removeChild(toast);
      }, 300);
    }, 3000);
  }

  /**
   * 格式化日期
   * @param {Date} date - 日期对象
   * @returns {string}
   */
  formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day} ${hours}:${minutes}`;
  }
}

export default MainPage;

class MathQuestTerrainMap {
  constructor(options) {
    this.canvas = options.canvas;
    this.ctx = this.canvas.getContext('2d');
    this.getView = options.getView;
    this.onViewChange = options.onViewChange || (() => {});
    this.onClickWorld = options.onClickWorld || (() => {});
    this.drawOverlay = options.drawOverlay || (() => {});
    this.image = null;
    this.imageKey = '';
    this.loadingKey = '';
    this.dragStart = null;
    this.bindEvents();
  }
  setView(view) {
    const normalized = {
      x: Math.round(Number(view.x || 0)),
      z: Math.round(Number(view.z || 0)),
      radius: Math.max(16, Math.min(1024, Math.round(Number(view.radius || 128)))),
      dimension: view.dimension || 'minecraft:overworld',
    };
    const key = this.key(normalized);
    if (key !== this.imageKey && key !== this.loadingKey) {
      this.load(normalized, key);
    }
    this.render();
  }
  key(view) {
    return `${view.dimension}|${view.x}|${view.z}|${view.radius}`;
  }
  load(view, key) {
    this.loadingKey = key;
    const img = new Image();
    const params = new URLSearchParams({
      dimension: view.dimension,
      x: String(view.x),
      z: String(view.z),
      radius: String(view.radius),
      size: '384',
      t: String(Date.now()),
    });
    img.onload = () => {
      this.image = img;
      this.imageKey = key;
      this.loadingKey = '';
      this.render();
    };
    img.onerror = () => {
      this.loadingKey = '';
      this.render();
    };
    img.src = `/api/terrain-map.png?${params.toString()}`;
  }
  render() {
    const view = this.getView();
    const ctx = this.ctx;
    const w = this.canvas.width;
    const h = this.canvas.height;
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#eef0e9';
    ctx.fillRect(0, 0, w, h);
    if (this.image) {
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(this.image, 0, 0, w, h);
    }
    this.drawGrid(ctx, view);
    this.drawCenter(ctx);
    this.drawOverlay(ctx, this);
  }
  drawGrid(ctx, view) {
    const w = this.canvas.width;
    const h = this.canvas.height;
    const step = Math.max(16, Math.pow(2, Math.round(Math.log2(view.radius / 4))));
    const minX = view.x - view.radius;
    const maxX = view.x + view.radius;
    const minZ = view.z - view.radius;
    const maxZ = view.z + view.radius;
    ctx.strokeStyle = 'rgba(32, 33, 36, 0.18)';
    ctx.lineWidth = 1;
    for (let x = Math.ceil(minX / step) * step; x <= maxX; x += step) {
      const p = this.worldToScreen(x, view.z);
      ctx.beginPath();
      ctx.moveTo(p.x, 0);
      ctx.lineTo(p.x, h);
      ctx.stroke();
    }
    for (let z = Math.ceil(minZ / step) * step; z <= maxZ; z += step) {
      const p = this.worldToScreen(view.x, z);
      ctx.beginPath();
      ctx.moveTo(0, p.y);
      ctx.lineTo(w, p.y);
      ctx.stroke();
    }
  }
  drawCenter(ctx) {
    const w = this.canvas.width;
    const h = this.canvas.height;
    ctx.strokeStyle = '#2f6f5e';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(w / 2 - 10, h / 2);
    ctx.lineTo(w / 2 + 10, h / 2);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(w / 2, h / 2 - 10);
    ctx.lineTo(w / 2, h / 2 + 10);
    ctx.stroke();
  }
  worldToScreen(x, z) {
    const view = this.getView();
    return {
      x: ((x - (view.x - view.radius)) / (view.radius * 2)) * this.canvas.width,
      y: ((z - (view.z - view.radius)) / (view.radius * 2)) * this.canvas.height,
    };
  }
  screenToWorld(clientX, clientY) {
    const rect = this.canvas.getBoundingClientRect();
    const view = this.getView();
    const x = clientX - rect.left;
    const y = clientY - rect.top;
    return {
      x: view.x - view.radius + (x / rect.width) * view.radius * 2,
      z: view.z - view.radius + (y / rect.height) * view.radius * 2,
    };
  }
  bindEvents() {
    this.canvas.addEventListener('wheel', event => {
      event.preventDefault();
      const view = this.getView();
      const factor = event.deltaY > 0 ? 1.25 : 0.8;
      this.onViewChange({ ...view, radius: Math.max(16, Math.min(1024, Math.round(view.radius * factor))) });
    }, { passive: false });
    this.canvas.addEventListener('pointerdown', event => {
      this.canvas.setPointerCapture(event.pointerId);
      this.dragStart = {
        x: event.clientX,
        y: event.clientY,
        view: this.getView(),
        moved: false,
      };
    });
    this.canvas.addEventListener('pointermove', event => {
      if (!this.dragStart) return;
      const dx = event.clientX - this.dragStart.x;
      const dy = event.clientY - this.dragStart.y;
      if (Math.abs(dx) + Math.abs(dy) < 4) return;
      this.dragStart.moved = true;
      const blocksX = dx / this.canvas.getBoundingClientRect().width * this.dragStart.view.radius * 2;
      const blocksZ = dy / this.canvas.getBoundingClientRect().height * this.dragStart.view.radius * 2;
      this.onViewChange({
        ...this.dragStart.view,
        x: Math.round(this.dragStart.view.x - blocksX),
        z: Math.round(this.dragStart.view.z - blocksZ),
      });
    });
    this.canvas.addEventListener('pointerup', event => {
      if (!this.dragStart) return;
      const wasDrag = this.dragStart.moved;
      this.dragStart = null;
      if (!wasDrag) {
        this.onClickWorld(this.screenToWorld(event.clientX, event.clientY));
      }
    });
  }
}

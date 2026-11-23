/**
 * AmbientBackground: Атмосферный зимний живой фон
 * Создает плавный дрейф снежинок, зимних кристаллов и легких пилюль с глубиной резкости
 */

export class AmbientBackground {
  constructor(canvasElement) {
    this.canvas = canvasElement;
    this.ctx = this.canvas.getContext('2d');
    this.particles = [];
    this.particleCount = 85; // Насыщенная зимняя атмосфера
    this.mouseX = 0;
    this.mouseY = 0;
    this.targetMouseX = 0;
    this.targetMouseY = 0;

    this.init();
  }

  init() {
    this.resize();
    window.addEventListener('resize', () => this.resize());
    window.addEventListener('mousemove', (e) => {
      this.targetMouseX = (e.clientX / window.innerWidth - 0.5) * 35;
      this.targetMouseY = (e.clientY / window.innerHeight - 0.5) * 22;
    });

    for (let i = 0; i < this.particleCount; i++) {
      this.particles.push(this.createParticle());
    }

    this.animate();
  }

  resize() {
    this.width = window.innerWidth;
    this.height = window.innerHeight;
    this.canvas.width = this.width;
    this.canvas.height = this.height;
  }

  createParticle(fromTop = false) {
    const rnd = Math.random();
    const isPill = rnd < 0.35; // ~35% частиц — парящие двухцветные капсулы
    const isSnowflake = !isPill && rnd < 0.72; // ~37% частиц — кристаллические снежинки
    const depth = Math.random(); // 0 (далеко) до 1 (близко)

    return {
      x: Math.random() * this.width,
      y: fromTop ? -25 : Math.random() * this.height,
      radius: isPill ? (depth * 5.5 + 4.5) : (depth * 4 + 2.5),
      speedY: depth * 0.85 + 0.45,
      speedX: (Math.random() - 0.5) * 0.35,
      angle: Math.random() * Math.PI * 2,
      angularSpeed: (Math.random() - 0.5) * 0.025,
      opacity: depth * 0.45 + 0.45,
      isPill,
      isSnowflake,
      depth,
      blur: (1 - depth) * 2
    };
  }

  drawSnowflake(ctx, size, opacity) {
    ctx.strokeStyle = `rgba(130, 190, 245, ${opacity * 0.95})`;
    ctx.lineWidth = 1.4;
    ctx.lineCap = 'round';
    
    // 6 лучей снежинки
    for (let i = 0; i < 6; i++) {
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.lineTo(0, size);
      // Маленькие ответвления на лучах
      ctx.moveTo(0, size * 0.55);
      ctx.lineTo(size * 0.25, size * 0.75);
      ctx.moveTo(0, size * 0.55);
      ctx.lineTo(-size * 0.25, size * 0.75);
      ctx.stroke();
      ctx.rotate(Math.PI / 3);
    }
  }

  animate() {
    this.ctx.clearRect(0, 0, this.width, this.height);

    // Плавный параллакс за курсором
    this.mouseX += (this.targetMouseX - this.mouseX) * 0.04;
    this.mouseY += (this.targetMouseY - this.mouseY) * 0.04;

    for (let i = 0; i < this.particles.length; i++) {
      const p = this.particles[i];

      p.y += p.speedY;
      p.x += p.speedX + Math.sin(p.angle * 1.5) * 0.35;
      p.angle += p.angularSpeed;

      // Перезапуск сверху при падении
      if (p.y > this.height + 30) {
        this.particles[i] = this.createParticle(true);
      }
      if (p.x > this.width + 30) p.x = -25;
      if (p.x < -30) p.x = this.width + 25;

      const drawX = p.x + this.mouseX * p.depth;
      const drawY = p.y + this.mouseY * p.depth;

      this.ctx.save();
      this.ctx.translate(drawX, drawY);

      if (p.isPill) {
        // Отрисовка четкой двухцветной пилюли
        this.ctx.rotate(p.angle);
        const w = p.radius * 2.4;
        const h = p.radius * 1.15;

        // Зеленая половинка капсулы
        this.ctx.fillStyle = `rgba(0, 176, 116, ${p.opacity * 0.75})`;
        this.ctx.beginPath();
        this.ctx.roundRect(-w / 2, -h / 2, w, h, h / 2);
        this.ctx.fill();

        // Белая половинка капсулы
        this.ctx.fillStyle = `rgba(255, 255, 255, ${p.opacity * 0.95})`;
        this.ctx.beginPath();
        this.ctx.roundRect(-w / 2, -h / 2, w / 2, h, [h / 2, 0, 0, h / 2]);
        this.ctx.fill();

        // Разделительный шов
        this.ctx.strokeStyle = `rgba(0, 140, 90, ${p.opacity * 0.55})`;
        this.ctx.lineWidth = 1.2;
        this.ctx.beginPath();
        this.ctx.moveTo(0, -h / 2);
        this.ctx.lineTo(0, h / 2);
        this.ctx.stroke();
      } else if (p.isSnowflake) {
        // Отрисовка кристаллической снежинки с вращением
        this.ctx.rotate(p.angle);
        this.drawSnowflake(this.ctx, p.radius * 1.6, p.opacity);
      } else {
        // Мягкая зимняя боке-частица с голубоватым свечением
        const grad = this.ctx.createRadialGradient(0, 0, 0, 0, 0, p.radius);
        grad.addColorStop(0, `rgba(180, 220, 255, ${p.opacity * 0.85})`);
        grad.addColorStop(1, `rgba(180, 220, 255, 0)`);
        this.ctx.fillStyle = grad;
        this.ctx.beginPath();
        this.ctx.arc(0, 0, p.radius * 1.5, 0, Math.PI * 2);
        this.ctx.fill();
      }

      this.ctx.restore();
    }

    requestAnimationFrame(() => this.animate());
  }
}

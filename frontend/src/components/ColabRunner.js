/**
 * ColabRunner: Интерактивная «Пилюля на прогулке» в стиле Google Colab Corgi/Cat mode
 * Регулярно пробегает через экран в праздничном новогоднем колпачке
 */

export class ColabRunner {
  constructor(containerElement) {
    this.container = containerElement;
    this.isRunning = false;
    this.timer = null;
    this.init();
  }

  init() {
    // Первый запуск через 3 секунды, затем каждые 14-22 секунды
    setTimeout(() => {
      this.runAcross();
      this.scheduleNextRun();
    }, 3000);
  }

  scheduleNextRun() {
    const nextInterval = 14000 + Math.random() * 8000;
    this.timer = setTimeout(() => {
      this.runAcross();
      this.scheduleNextRun();
    }, nextInterval);
  }

  runAcross() {
    if (this.isRunning) return;
    this.isRunning = true;

    // Случайное направление: 50% слева направо, 50% справа налево
    const goingRight = Math.random() < 0.5;
    // Случайная дорожка: 50% сверху под гирляндой, 50% снизу вдоль нижней кромки
    const isTopLane = Math.random() < 0.5;

    const runner = document.createElement('div');
    runner.className = `colab-runner-mascot tap-effect ${goingRight ? 'going-right' : 'going-left'} ${isTopLane ? 'lane-top' : 'lane-bottom'}`;
    runner.title = 'Поймай меня! Нажми для пожелания здоровья';

    const startX = goingRight ? -90 : (window.innerWidth + 90);
    const targetX = goingRight ? (window.innerWidth + 90) : -90;

    runner.style.transform = `translateX(${startX}px)`;
    if (isTopLane) {
      runner.style.top = '14px';
      runner.style.bottom = 'auto';
    } else {
      runner.style.top = 'auto';
      runner.style.bottom = '14px'; // Прямо внизу вдоль футера
    }

    runner.innerHTML = `
      <div class="colab-hitbox">
        <!-- Внутренний контейнер с разворотом силуэта -->
        <div class="colab-runner-inner ${goingRight ? '' : 'flipped'}">
          <!-- Единый векторный силуэт: капсула + шапка СВЕРХУ капсулы -->
          <svg class="colab-unified-mascot" viewBox="0 0 56 75" fill="none">
            <!-- 1. Нижняя зеленая половина капсулы -->
            <path d="M14 42V56C14 63.7 20.3 70 28 70C35.7 70 42 63.7 42 56V42H14Z" fill="#00B074"/>
            <!-- 2. Верхняя белая половина капсулы -->
            <path d="M14 42V28C14 20.3 20.3 14 28 14C35.7 14 42 20.3 42 28V42H14Z" fill="#FFFFFF" stroke="#ECEFF2" stroke-width="1.2"/>
            <!-- 3. Глазки и улыбка -->
            <circle cx="23" cy="34" r="2.2" fill="#181C20"/>
            <circle cx="33" cy="34" r="2.2" fill="#181C20"/>
            <path d="M25 38C25 38 28 41 31 38" stroke="#181C20" stroke-width="1.6" stroke-linecap="round"/>

            <!-- 4. Новогодняя шапка строго ПОВЕРХ капсулы (передний слой, закрывает купол) -->
            <path d="M10 16 C 10 5, 20 -2, 28 -2 C 38 -2, 47 5, 47 13 C 47 16, 45 19, 42 16 C 41 13, 41 12, 40 12 Z" fill="#E53935"/>
            <circle cx="46.5" cy="16" r="4.5" fill="#FFFFFF" stroke="#ECEFF2" stroke-width="1"/>
            <circle cx="45.5" cy="15" r="1.5" fill="#F8FAFC"/>
            <path d="M9 17 C 14 12, 40 10, 46 15 C 47 19, 42 20, 28 20 C 14 20, 8 19, 9 17 Z" fill="#FFFFFF" stroke="#ECEFF2" stroke-width="1.2"/>
          </svg>

          <!-- Бегущие ножки -->
          <div class="colab-legs">
            <span class="colab-leg left"></span>
            <span class="colab-leg right"></span>
          </div>
        </div>

        <!-- Облачко реплики (НЕ внутри flipped, чтобы текст никогда не зеркалился!) -->
        <div class="colab-speech-popup ${isTopLane ? 'show-below' : 'show-above'}">
          Будьте здоровы!
        </div>
      </div>
    `;

    let isPaused = false;
    let duration = 14;

    // Клик по маскоту: пауза, мягкий прыжок и появление реплики прямо над ним без сдвигов
    runner.addEventListener('click', (e) => {
      e.stopPropagation();
      if (isPaused) return;
      isPaused = true;

      const computedStyle = window.getComputedStyle(runner);
      const matrix = new DOMMatrixReadOnly(computedStyle.transform);
      const currentX = matrix.m41;

      runner.style.transition = 'none';
      runner.style.transform = `translateX(${currentX}px)`;
      runner.classList.add('jump-gentle');

      const popup = runner.querySelector('.colab-speech-popup');
      if (popup) popup.classList.add('visible');

      setTimeout(() => {
        if (!runner.isConnected) return;
        if (popup) popup.classList.remove('visible');
        runner.classList.remove('jump-gentle');

        const remainingDistance = Math.abs(targetX - currentX);
        const totalDistance = Math.abs(targetX - startX);
        const remainingTime = Math.max(2, (remainingDistance / totalDistance) * duration);

        runner.style.transition = `transform ${remainingTime}s linear`;
        runner.style.transform = `translateX(${targetX}px)`;
        isPaused = false;
      }, 1600);
    });

    runner.addEventListener('transitionend', (e) => {
      if (e.target === runner && !isPaused) {
        runner.remove();
        this.isRunning = false;
      }
    });

    document.body.appendChild(runner);

    requestAnimationFrame(() => {
      runner.style.transition = `transform ${duration}s linear`;
      runner.style.transform = `translateX(${targetX}px)`;
    });

    setTimeout(() => {
      if (runner.isConnected) {
        runner.remove();
        this.isRunning = false;
      }
    }, (duration + 5) * 1000);
  }
}

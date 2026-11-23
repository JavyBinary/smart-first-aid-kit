/**
 * Mascot: Векторный интерактивный маскот «Пилюля» в новогоднем колпачке
 */

export class Mascot {
  constructor(containerElement, options = {}) {
    this.container = containerElement;
    this.compact = options.compact || false;
    this.state = 'idle'; // 'idle' | 'thinking' | 'happy' | 'emergency'
    this.render();
  }

  setState(newState, speechText = '') {
    this.state = newState;
    this.container.className = `mascot-container ${newState} ${this.compact ? 'compact' : ''}`;
    const bubble = this.container.querySelector('.mascot-speech-bubble');
    if (bubble) {
      if (speechText) {
        bubble.textContent = speechText;
        bubble.style.display = 'block';
      } else {
        bubble.style.display = 'none';
      }
    }
  }

  render() {
    this.container.className = `mascot-container ${this.compact ? 'compact' : ''}`;
    this.container.innerHTML = `
      <div class="mascot-svg-wrap">
        <!-- Единый векторный маскот: капсула + праздничная шапка Деда Мороза -->
        <svg class="mascot-svg" viewBox="0 0 100 120" fill="none">
          <!-- Тень под капсулой -->
          <ellipse cx="50" cy="115" rx="30" ry="5" fill="rgba(0,0,0,0.08)"/>

          <!-- Нижняя изумрудная половинка капсулы -->
          <path d="M22 60V86C22 101.464 34.536 114 50 114C65.464 114 78 101.464 78 86V60H22Z" fill="#00B074"/>

          <!-- Верхняя белая половинка капсулы -->
          <path d="M22 60V34C22 18.536 34.536 6 50 6C65.464 6 78 18.536 78 34V60H22Z" fill="#FFFFFF" stroke="#ECEFF2" stroke-width="1.5"/>

          <!-- Глазки с анимацией моргания -->
          <g class="mascot-eyes">
            <circle cx="41" cy="48" r="4.5" fill="#181C20"/>
            <circle cx="59" cy="48" r="4.5" fill="#181C20"/>
            <!-- Блики в глазах -->
            <circle cx="42.5" cy="46.5" r="1.5" fill="#FFFFFF"/>
            <circle cx="60.5" cy="46.5" r="1.5" fill="#FFFFFF"/>
          </g>

          <!-- Румяные щёчки -->
          <ellipse cx="33" cy="55" rx="3.8" ry="2.2" fill="rgba(255, 120, 120, 0.4)"/>
          <ellipse cx="67" cy="55" rx="3.8" ry="2.2" fill="rgba(255, 120, 120, 0.4)"/>

          <!-- Дружелюбная улыбка -->
          <path d="M44 56C44 56 50 62 56 56" stroke="#181C20" stroke-width="2.5" stroke-linecap="round"/>

          <!-- Маленькие ручки -->
          <path d="M19 65C13 67 12 74 15 78" stroke="#00B074" stroke-width="4" stroke-linecap="round"/>
          <path d="M81 65C87 67 88 74 85 78" stroke="#00B074" stroke-width="4" stroke-linecap="round"/>

          <!-- Новогодняя шапочка Деда Мороза (строго поверх купола, полностью укутывает макушку) -->
          <g class="mascot-santa-hat-group">
            <!-- 1. Красный бархатный колпак: начинается от опушки и полностью закрывает купол (выходит выше y=6) -->
            <path d="M20 25 C 20 8, 36 -2, 50 -2 C 68 -2, 84 8, 84 22 C 84 27, 80 32, 75 28 C 74 23, 74 21, 72 21 Z" fill="#E53935"/>
            <path d="M24 22 C 32 8, 56 4, 76 16" stroke="#D32F2F" stroke-width="1.8" stroke-linecap="round"/>

            <!-- 2. Пушистый белоснежный помпон на кончике колпака -->
            <circle cx="83" cy="28" r="8" fill="#FFFFFF" stroke="#ECEFF2" stroke-width="1.2"/>
            <circle cx="81.5" cy="26.5" r="3" fill="#F8FAFC"/>

            <!-- 3. Белоснежная меховая опушка: мягкий валик поперек лба над глазами -->
            <path d="M18 26 C 26 18, 72 16, 82 24 C 84 31, 76 33, 50 32 C 24 33, 16 31, 18 26 Z" fill="#FFFFFF" stroke="#ECEFF2" stroke-width="1.5" filter="drop-shadow(0 2px 4px rgba(0,0,0,0.12))"/>
          </g>
        </svg>
      </div>
      <div class="mascot-speech-bubble" style="display: none;"></div>
    `;
  }
}

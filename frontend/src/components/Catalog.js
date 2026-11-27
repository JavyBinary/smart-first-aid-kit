/**
 * Catalog: Расширенная настраиваемая витрина лекарств («Аптека»)
 * Уникальные препараты с выбором дозировки/формы, настраиваемым сроком годности и количеством.
 */

import { store } from '../state/store.js';
import { kitApi } from '../api/kit.api.js';

function futureDate(monthsAhead = 18) {
  const d = new Date();
  d.setMonth(d.getMonth() + monthsAhead);
  return d.toISOString().slice(0, 10);
}

export const CATALOG_DATABASE = [
  // 1. Обезболивающие и жаропонижающие
  {
    id: 'cat_1',
    name: 'Ибупрофен (Нурофен)',
    category: 'Обезболивающие',
    tags: ['боль', 'головная боль', 'жар', 'зубная боль', 'воспаление'],
    status: 'otc',
    expiry: futureDate(22),
    iconColor: '#E8F7F0',
    variants: [
      { label: '200 мг · 16 капсул', dosage: '200 мг · 16 шт.', form: 'капсулы' },
      { label: '400 мг · 10 таблеток', dosage: '400 мг · 10 шт.', form: 'таблетки' },
      { label: 'Суспензия 100 мг/5 мл · 150 мл', dosage: '100 мг/5 мл · 150 мл', form: 'сироп' },
    ],
  },
  {
    id: 'cat_2',
    name: 'Парацетамол',
    category: 'Обезболивающие',
    tags: ['жар', 'боль', 'простуда', 'головная боль', 'температура'],
    status: 'otc',
    expiry: futureDate(24),
    iconColor: '#FFF3E8',
    variants: [
      { label: '500 мг · 20 таблеток', dosage: '500 мг · 20 шт.', form: 'таблетки' },
      { label: '200 мг · 20 таблеток', dosage: '200 мг · 20 шт.', form: 'таблетки' },
      { label: 'Сироп 120 мг/5 мл · 100 мл', dosage: '120 мг/5 мл · 100 мл', form: 'сироп' },
    ],
  },
  {
    id: 'cat_3',
    name: 'Пенталгин',
    category: 'Обезболивающие',
    tags: ['боль', 'спазм', 'мигрень', 'зубная боль'],
    status: 'otc',
    expiry: futureDate(18),
    iconColor: '#E8F1FF',
    variants: [
      { label: 'Таблетки · 12 шт.', dosage: 'комб. · 12 шт.', form: 'таблетки' },
      { label: 'Таблетки · 24 шт.', dosage: 'комб. · 24 шт.', form: 'таблетки' },
    ],
  },
  {
    id: 'cat_4',
    name: 'Нимесулид (Нимесил)',
    category: 'Обезболивающие',
    tags: ['сильная боль', 'воспаление', 'зубная боль', 'спина'],
    status: 'rx',
    expiry: futureDate(20),
    iconColor: '#FFF0F0',
    variants: [
      { label: 'Порошок 100 мг · 9 пак.', dosage: '100 мг · 9 пак.', form: 'порошок' },
      { label: 'Порошок 100 мг · 30 пак.', dosage: '100 мг · 30 пак.', form: 'порошок' },
      { label: 'Таблетки 100 мг · 20 шт.', dosage: '100 мг · 20 шт.', form: 'таблетки' },
    ],
  },
  {
    id: 'cat_5',
    name: 'Кеторолак (Кетанов)',
    category: 'Обезболивающие',
    tags: ['сильная боль', 'зубная боль', 'травмы'],
    status: 'rx',
    expiry: futureDate(21),
    iconColor: '#FFF0F0',
    variants: [
      { label: 'Таблетки 10 мг · 20 шт.', dosage: '10 мг · 20 шт.', form: 'таблетки' },
      { label: 'Таблетки 10 мг · 10 шт.', dosage: '10 мг · 10 шт.', form: 'таблетки' },
    ],
  },
  {
    id: 'cat_6',
    name: 'Ацетилсалициловая кислота (Аспирин)',
    category: 'Обезболивающие',
    tags: ['жар', 'боль', 'головная боль', 'кровь'],
    status: 'otc',
    expiry: futureDate(26),
    iconColor: '#FFF8E6',
    variants: [
      { label: 'Таблетки 500 мг · 20 шт.', dosage: '500 мг · 20 шт.', form: 'таблетки' },
      { label: 'Шипучие 500 мг · 10 шт.', dosage: 'шипучие 500 мг · 10 шт.', form: 'таблетки' },
      { label: 'Кардио 100 мг · 30 шт.', dosage: '100 мг · 30 шт.', form: 'таблетки' },
    ],
  },
  {
    id: 'cat_7',
    name: 'Декскетопрофен (Дексалгин)',
    category: 'Обезболивающие',
    tags: ['боль', 'зубная боль', 'суставы', 'воспаление'],
    status: 'rx',
    expiry: futureDate(19),
    iconColor: '#E8F1FF',
    variants: [
      { label: 'Таблетки 25 мг · 10 шт.', dosage: '25 мг · 10 шт.', form: 'таблетки' },
      { label: 'Саше 25 мг · 10 пак.', dosage: '25 мг · 10 пак.', form: 'порошок' },
    ],
  },
  {
    id: 'cat_8',
    name: 'Цитрамон П',
    category: 'Обезболивающие',
    tags: ['головная боль', 'низкое давление', 'усталость'],
    status: 'otc',
    expiry: futureDate(24),
    iconColor: '#FFF3E8',
    variants: [
      { label: 'Таблетки · 20 шт.', dosage: '240+180+30 мг · 20 шт.', form: 'таблетки' },
      { label: 'Таблетки · 40 шт.', dosage: '240+180+30 мг · 40 шт.', form: 'таблетки' },
    ],
  },

  // 2. Простуда и грипп
  {
    id: 'cat_9',
    name: 'Терафлю',
    category: 'Простуда и грипп',
    tags: ['простуда', 'жар', 'насморк', 'озноб', 'грипп'],
    status: 'otc',
    expiry: futureDate(18),
    iconColor: '#FFF8E6',
    variants: [
      { label: 'Порошок лимон · 10 пак.', dosage: '325+10+20 мг · 10 пак.', form: 'порошок' },
      { label: 'Экстра · 10 пак.', dosage: '650+10+20 мг · 10 пак.', form: 'порошок' },
    ],
  },
  {
    id: 'cat_10',
    name: 'Колдрекс ХотРем',
    category: 'Простуда и грипп',
    tags: ['простуда', 'жар', 'грипп', 'озноб'],
    status: 'otc',
    expiry: futureDate(20),
    iconColor: '#FFF3E8',
    variants: [
      { label: 'Порошок лимон 750 мг · 10 пак.', dosage: '750 мг · 10 пак.', form: 'порошок' },
      { label: 'МаксГрипп 1000 мг · 10 пак.', dosage: '1000 мг · 10 пак.', form: 'порошок' },
    ],
  },
  {
    id: 'cat_11',
    name: 'Ринза / Ринзасип',
    category: 'Простуда и грипп',
    tags: ['простуда', 'жар', 'насморк'],
    status: 'otc',
    expiry: futureDate(22),
    iconColor: '#EBF5FB',
    variants: [
      { label: 'Таблетки · 10 шт.', dosage: '500 мг · 10 шт.', form: 'таблетки' },
      { label: 'Порошок с вит. C · 10 пак.', dosage: '750 мг · 10 пак.', form: 'порошок' },
    ],
  },
  {
    id: 'cat_12',
    name: 'Аскорбиновая кислота (Витамин C)',
    category: 'Простуда и грипп',
    tags: ['простуда', 'иммунитет', 'витамины'],
    status: 'otc',
    expiry: futureDate(28),
    iconColor: '#FFF8E6',
    variants: [
      { label: 'Шипучие 1000 мг · 20 шт.', dosage: '1000 мг · 20 шт.', form: 'таблетки' },
      { label: 'Драже 50 мг · 200 шт.', dosage: '50 мг · 200 шт.', form: 'таблетки' },
    ],
  },

  // 3. Горло и кашель
  {
    id: 'cat_13',
    name: 'Стрепсилс',
    category: 'Горло и кашель',
    tags: ['горло', 'боль в горле', 'першение', 'фарингит'],
    status: 'otc',
    expiry: futureDate(24),
    iconColor: '#FFF8E6',
    variants: [
      { label: 'Мед и лимон · 24 паст.', dosage: '1.2+0.6 мг · 24 шт.', form: 'пастилки' },
      { label: 'Интенсив с флурбипрофеном · 16 шт.', dosage: '8.75 мг · 16 шт.', form: 'пастилки' },
    ],
  },
  {
    id: 'cat_14',
    name: 'Ацетилцистеин (АЦЦ)',
    category: 'Горло и кашель',
    tags: ['кашель', 'мокрота', 'бронхит'],
    status: 'otc',
    expiry: futureDate(22),
    iconColor: '#E8F7F0',
    variants: [
      { label: 'АЦЦ Лонг 600 мг · 10 шип. таб.', dosage: '600 мг · 10 шт.', form: 'таблетки' },
      { label: 'АЦЦ 200 мг · 20 пак.', dosage: '200 мг · 20 пак.', form: 'порошок' },
      { label: 'Сироп 20 мг/мл · 100 мл', dosage: '20 мг/мл · 100 мл', form: 'сироп' },
    ],
  },
  {
    id: 'cat_15',
    name: 'Амброксол (Лазолван)',
    category: 'Горло и кашель',
    tags: ['кашель', 'мокрота', 'бронхит'],
    status: 'otc',
    expiry: futureDate(25),
    iconColor: '#EBF5FB',
    variants: [
      { label: 'Таблетки 30 мг · 20 шт.', dosage: '30 мг · 20 шт.', form: 'таблетки' },
      { label: 'Сироп 30 мг/5 мл · 100 мл', dosage: '30 мг/5 мл · 100 мл', form: 'сироп' },
    ],
  },
  {
    id: 'cat_16',
    name: 'Гексорал / Тантум Верде',
    category: 'Горло и кашель',
    tags: ['горло', 'ангина', 'тонзиллит', 'антисептик'],
    status: 'otc',
    expiry: futureDate(23),
    iconColor: '#E8F7F0',
    variants: [
      { label: 'Спрей 0.15% · 30 мл', dosage: '0.15% · 30 мл', form: 'спрей' },
      { label: 'Таблетки для рассасывания · 20 шт.', dosage: '3 мг · 20 шт.', form: 'пастилки' },
    ],
  },
  {
    id: 'cat_17',
    name: 'Синекод (Бутамират)',
    category: 'Горло и кашель',
    tags: ['сухой кашель', 'кашель'],
    status: 'otc',
    expiry: futureDate(21),
    iconColor: '#F5EEF8',
    variants: [
      { label: 'Сироп 1.5 мг/мл · 200 мл', dosage: '1.5 мг/мл · 200 мл', form: 'сироп' },
      { label: 'Капли для детей · 20 мл', dosage: '5 мг/мл · 20 мл', form: 'капли' },
    ],
  },

  // 4. Нос и глаза
  {
    id: 'cat_18',
    name: 'Ксилометазолин (Снуп / Отривин)',
    category: 'Нос и глаза',
    tags: ['насморк', 'заложенность носа', 'синусит'],
    status: 'otc',
    expiry: futureDate(24),
    iconColor: '#EBF5FB',
    variants: [
      { label: 'Спрей 0.1% (взрослый) · 15 мл', dosage: '0.1% · 15 мл', form: 'спрей' },
      { label: 'Спрей 0.05% (детский) · 15 мл', dosage: '0.05% · 15 мл', form: 'спрей' },
    ],
  },
  {
    id: 'cat_19',
    name: 'Аква Марис (Морская вода)',
    category: 'Нос и глаза',
    tags: ['насморк', 'промывание носа', 'аллергия'],
    status: 'otc',
    expiry: futureDate(30),
    iconColor: '#EBF5FB',
    variants: [
      { label: 'Изотонический спрей · 50 мл', dosage: 'морская вода · 50 мл', form: 'спрей' },
      { label: 'Стронг (гипертонический) · 30 мл', dosage: 'морская вода стронг · 30 мл', form: 'спрей' },
    ],
  },
  {
    id: 'cat_20',
    name: 'Сульфацил натрия (Альбуцид)',
    category: 'Нос и глаза',
    tags: ['глаза', 'конъюнктивит', 'воспаление'],
    status: 'otc',
    expiry: futureDate(18),
    iconColor: '#E8F1FF',
    variants: [
      { label: 'Капли глазные 20% · 10 мл', dosage: '20% · 10 мл', form: 'капли' },
      { label: 'Капли глазные 20% · 5 мл', dosage: '20% · 5 мл', form: 'капли' },
    ],
  },
  {
    id: 'cat_21',
    name: 'Систейн / Гилан (Искусственная слеза)',
    category: 'Нос и глаза',
    tags: ['глаза', 'сухость глаз', 'раздражение'],
    status: 'otc',
    expiry: futureDate(20),
    iconColor: '#E8F7F0',
    variants: [
      { label: 'Капли увлажняющие · 10 мл', dosage: '0.18% · 10 мл', form: 'капли' },
      { label: 'Юнидозы 0.4 мл · 30 шт.', dosage: '0.18% · 30 доз', form: 'капли' },
    ],
  },

  // 5. ЖКТ и пищеварение
  {
    id: 'cat_22',
    name: 'Смекта (Диосмектит)',
    category: 'ЖКТ и пищеварение',
    tags: ['диарея', 'понос', 'отравление', 'ЖКТ', 'изжога'],
    status: 'otc',
    expiry: futureDate(26),
    iconColor: '#FFF3E8',
    variants: [
      { label: 'Порошок 3 г (апельсин) · 10 пак.', dosage: '3 г · 10 пак.', form: 'порошок' },
      { label: 'Суспензия готовая · 12 пак.', dosage: '3 г · 12 саше', form: 'раствор' },
    ],
  },
  {
    id: 'cat_23',
    name: 'Полисорб МП',
    category: 'ЖКТ и пищеварение',
    tags: ['отравление', 'детокс', 'диарея', 'аллергия'],
    status: 'otc',
    expiry: futureDate(36),
    iconColor: '#FFF8E6',
    variants: [
      { label: 'Порошок банка · 25 г', dosage: 'банка 25 г', form: 'порошок' },
      { label: 'Порошок банка · 50 г', dosage: 'банка 50 г', form: 'порошок' },
      { label: 'Саше 3 г · 10 шт.', dosage: '3 г · 10 пак.', form: 'порошок' },
    ],
  },
  {
    id: 'cat_24',
    name: 'Активированный уголь / Энтеросгель',
    category: 'ЖКТ и пищеварение',
    tags: ['отравление', 'метеоризм', 'ЖКТ', 'вздутие'],
    status: 'otc',
    expiry: futureDate(28),
    iconColor: '#F1F5F9',
    variants: [
      { label: 'Уголь 250 мг · 30 таблеток', dosage: '250 мг · 30 шт.', form: 'таблетки' },
      { label: 'Энтеросгель туба · 225 г', dosage: 'паста · 225 г', form: 'мазь' },
    ],
  },
  {
    id: 'cat_25',
    name: 'Панкреатин (Мезим Форте / Креон)',
    category: 'ЖКТ и пищеварение',
    tags: ['ЖКТ', 'тяжесть', 'переедание', 'ферменты'],
    status: 'otc',
    expiry: futureDate(24),
    iconColor: '#F5EEF8',
    variants: [
      { label: 'Мезим 10 000 ЕД · 20 таб.', dosage: '10 000 ЕД · 20 шт.', form: 'таблетки' },
      { label: 'Креон 10 000 · 20 капс.', dosage: '10 000 ЕД · 20 капс.', form: 'капсулы' },
      { label: 'Креон 25 000 · 20 капс.', dosage: '25 000 ЕД · 20 капс.', form: 'капсулы' },
    ],
  },
  {
    id: 'cat_26',
    name: 'Омепразол',
    category: 'ЖКТ и пищеварение',
    tags: ['ЖКТ', 'изжога', 'гастрит', 'желудок'],
    status: 'otc',
    expiry: futureDate(24),
    iconColor: '#E8F7F0',
    variants: [
      { label: 'Капсулы 20 мг · 30 шт.', dosage: '20 мг · 30 шт.', form: 'капсулы' },
      { label: 'Капсулы 40 мг · 28 шт.', dosage: '40 мг · 28 шт.', form: 'капсулы' },
    ],
  },
  {
    id: 'cat_27',
    name: 'Ренни / Гевискон',
    category: 'ЖКТ и пищеварение',
    tags: ['изжога', 'кислотность', 'ЖКТ'],
    status: 'otc',
    expiry: futureDate(24),
    iconColor: '#EBF5FB',
    variants: [
      { label: 'Ренни мята · 24 жев. таб.', dosage: '680+80 мг · 24 шт.', form: 'таблетки' },
      { label: 'Гевискон суспензия · 150 мл', dosage: '150 мл', form: 'раствор' },
    ],
  },
  {
    id: 'cat_28',
    name: 'Лоперамид (Имодиум)',
    category: 'ЖКТ и пищеварение',
    tags: ['диарея', 'понос', 'ЖКТ'],
    status: 'otc',
    expiry: futureDate(26),
    iconColor: '#FFF3E8',
    variants: [
      { label: 'Капсулы 2 мг · 20 шт.', dosage: '2 мг · 20 шт.', form: 'капсулы' },
      { label: 'Таблетки для рассасывания · 10 шт.', dosage: '2 мг · 10 шт.', form: 'таблетки' },
    ],
  },
  {
    id: 'cat_29',
    name: 'Регидрон',
    category: 'ЖКТ и пищеварение',
    tags: ['обезвоживание', 'диарея', 'рвота', 'отравление'],
    status: 'otc',
    expiry: futureDate(30),
    iconColor: '#E8F7F0',
    variants: [
      { label: 'Порошок 18.9 г · 10 пак.', dosage: '18.9 г · 10 пак.', form: 'порошок' },
      { label: 'Порошок 18.9 г · 4 пак.', dosage: '18.9 г · 4 пак.', form: 'порошок' },
    ],
  },
  {
    id: 'cat_30',
    name: 'Эспумизан (Симетикон)',
    category: 'ЖКТ и пищеварение',
    tags: ['вздутие', 'метеоризм', 'колики', 'ЖКТ'],
    status: 'otc',
    expiry: futureDate(26),
    iconColor: '#FFF8E6',
    variants: [
      { label: 'Капсулы 40 мг · 25 шт.', dosage: '40 мг · 25 шт.', form: 'капсулы' },
      { label: 'Эспумизан L капли · 30 мл', dosage: '40 мг/мл · 30 мл', form: 'капли' },
    ],
  },

  // 6. Спазмолитики
  {
    id: 'cat_31',
    name: 'Дротаверин (Но-Шпа)',
    category: 'Спазмолитики',
    tags: ['спазм', 'боль', 'живот', 'ЖКТ', 'колики'],
    status: 'otc',
    expiry: futureDate(28),
    iconColor: '#FFF8E6',
    variants: [
      { label: 'Но-Шпа 40 мг · 24 таблетки', dosage: '40 мг · 24 шт.', form: 'таблетки' },
      { label: 'Но-Шпа Форте 80 мг · 20 таб.', dosage: '80 мг · 20 шт.', form: 'таблетки' },
      { label: 'Дротаверин 40 мг · 40 таб.', dosage: '40 мг · 40 шт.', form: 'таблетки' },
    ],
  },
  {
    id: 'cat_32',
    name: 'Спазмалгон',
    category: 'Спазмолитики',
    tags: ['спазм', 'колики', 'живот', 'головная боль'],
    status: 'otc',
    expiry: futureDate(22),
    iconColor: '#E8F1FF',
    variants: [
      { label: 'Таблетки · 20 шт.', dosage: '500 мг · 20 шт.', form: 'таблетки' },
      { label: 'Таблетки · 50 шт.', dosage: '500 мг · 50 шт.', form: 'таблетки' },
    ],
  },
  {
    id: 'cat_33',
    name: 'Тримебутин (Тримедат)',
    category: 'Спазмолитики',
    tags: ['спазм', 'ЖКТ', 'живот', 'вздутие'],
    status: 'otc',
    expiry: futureDate(24),
    iconColor: '#E8F7F0',
    variants: [
      { label: 'Таблетки 100 мг · 30 шт.', dosage: '100 мг · 30 шт.', form: 'таблетки' },
      { label: 'Таблетки 200 мг · 30 шт.', dosage: '200 мг · 30 шт.', form: 'таблетки' },
    ],
  },

  // 7. Аллергия
  {
    id: 'cat_34',
    name: 'Цетиризин (Зодак / Цетрин)',
    category: 'Аллергия',
    tags: ['аллергия', 'зуд', 'ринит', 'чихание', 'крапивница'],
    status: 'otc',
    expiry: futureDate(28),
    iconColor: '#E8F1FF',
    variants: [
      { label: 'Таблетки 10 мг · 20 шт.', dosage: '10 мг · 20 шт.', form: 'таблетки' },
      { label: 'Капли 10 мг/мл · 20 мл', dosage: '10 мг/мл · 20 мл', form: 'капли' },
    ],
  },
  {
    id: 'cat_35',
    name: 'Лоратадин (Кларитин)',
    category: 'Аллергия',
    tags: ['аллергия', 'зуд', 'крапивница', 'ринит'],
    status: 'otc',
    expiry: futureDate(26),
    iconColor: '#E8F7F0',
    variants: [
      { label: 'Таблетки 10 мг · 10 шт.', dosage: '10 мг · 10 шт.', form: 'таблетки' },
      { label: 'Таблетки 10 мг · 30 шт.', dosage: '10 мг · 30 шт.', form: 'таблетки' },
      { label: 'Сироп 1 мг/мл · 120 мл', dosage: '1 мг/мл · 120 мл', form: 'сироп' },
    ],
  },
  {
    id: 'cat_36',
    name: 'Супрастин (Хлоропирамин)',
    category: 'Аллергия',
    tags: ['аллергия', 'отек', 'укус', 'крапивница'],
    status: 'otc',
    expiry: futureDate(22),
    iconColor: '#FFF3E8',
    variants: [
      { label: 'Таблетки 25 мг · 20 шт.', dosage: '25 мг · 20 шт.', form: 'таблетки' },
      { label: 'Таблетки 25 мг · 40 шт.', dosage: '25 мг · 40 шт.', form: 'таблетки' },
    ],
  },
  {
    id: 'cat_37',
    name: 'Фенистил гель',
    category: 'Аллергия',
    tags: ['зуд', 'укусы', 'аллергия', 'кожа'],
    status: 'otc',
    expiry: futureDate(24),
    iconColor: '#EBF5FB',
    variants: [
      { label: 'Гель 0.1% · 30 г', dosage: '0.1% · 30 г', form: 'мазь' },
      { label: 'Гель 0.1% · 50 г', dosage: '0.1% · 50 г', form: 'мазь' },
    ],
  },

  // 8. Антисептики и кожа
  {
    id: 'cat_38',
    name: 'Хлоргексидин',
    category: 'Антисептики и кожа',
    tags: ['антисептик', 'раны', 'порез', 'дезинфекция'],
    status: 'otc',
    expiry: futureDate(26),
    iconColor: '#EBF5FB',
    variants: [
      { label: 'Водный р-р 0.05% · 100 мл', dosage: '0.05% · 100 мл', form: 'раствор' },
      { label: 'Спрей 0.05% · 100 мл', dosage: '0.05% · 100 мл', form: 'спрей' },
    ],
  },
  {
    id: 'cat_39',
    name: 'Мирамистин',
    category: 'Антисептики и кожа',
    tags: ['антисептик', 'горло', 'раны', 'ожоги'],
    status: 'otc',
    expiry: futureDate(26),
    iconColor: '#EBF5FB',
    variants: [
      { label: 'Раствор с насадкой · 150 мл', dosage: '0.01% · 150 мл', form: 'спрей' },
      { label: 'Раствор флакон · 50 мл', dosage: '0.01% · 50 мл', form: 'раствор' },
    ],
  },
  {
    id: 'cat_40',
    name: 'Перекись водорода',
    category: 'Антисептики и кожа',
    tags: ['антисептик', 'раны', 'кровь', 'порез'],
    status: 'otc',
    expiry: futureDate(20),
    iconColor: '#F1F5F9',
    variants: [
      { label: 'Раствор 3% · 100 мл', dosage: '3% · 100 мл', form: 'раствор' },
      { label: 'Спрей 3% · 50 мл', dosage: '3% · 50 мл', form: 'спрей' },
    ],
  },
  {
    id: 'cat_41',
    name: 'Декспантенол (Бепантен / Пантенол)',
    category: 'Антисептики и кожа',
    tags: ['ожоги', 'ссадины', 'кожа', 'порез'],
    status: 'otc',
    expiry: futureDate(24),
    iconColor: '#FFF0F0',
    variants: [
      { label: 'Мазь 5% · 30 г', dosage: '5% · 30 г', form: 'мазь' },
      { label: 'Мазь 5% · 100 г', dosage: '5% · 100 г', form: 'мазь' },
      { label: 'Спрей-пена 4.6% · 130 г', dosage: '4.6% · 130 г', form: 'спрей' },
    ],
  },
  {
    id: 'cat_42',
    name: 'Левомеколь / Банеоцин',
    category: 'Антисептики и кожа',
    tags: ['раны', 'воспаление', 'кожа', 'инфекция'],
    status: 'otc',
    expiry: futureDate(22),
    iconColor: '#FFF3E8',
    variants: [
      { label: 'Левомеколь мазь · 40 г', dosage: '40 г', form: 'мазь' },
      { label: 'Банеоцин порошок · 10 г', dosage: '10 г', form: 'порошок' },
    ],
  },

  // 9. Сердце и давление
  {
    id: 'cat_43',
    name: 'Нитроглицерин',
    category: 'Сердце и давление',
    tags: ['сердце', 'стенокардия', 'боль в груди'],
    status: 'rx',
    expiry: futureDate(18),
    iconColor: '#FFF0F0',
    variants: [
      { label: 'Таблетки 0.5 мг · 40 шт.', dosage: '0.5 мг · 40 шт.', form: 'таблетки' },
      { label: 'Нитроспрей 0.4 мг/доза · 10 г', dosage: '0.4 мг/доза · 200 доз', form: 'спрей' },
    ],
  },
  {
    id: 'cat_44',
    name: 'Валидол',
    category: 'Сердце и давление',
    tags: ['сердце', 'укачивание', 'тревога'],
    status: 'otc',
    expiry: futureDate(24),
    iconColor: '#E8F7F0',
    variants: [
      { label: 'Таблетки подъязычные 60 мг · 10 шт.', dosage: '60 мг · 10 шт.', form: 'таблетки' },
      { label: 'Капсулы 100 мг · 20 шт.', dosage: '100 мг · 20 шт.', form: 'капсулы' },
    ],
  },
  {
    id: 'cat_45',
    name: 'Корвалол',
    category: 'Сердце и давление',
    tags: ['сердце', 'тахикардия', 'бессонница', 'тревога'],
    status: 'otc',
    expiry: futureDate(28),
    iconColor: '#F5EEF8',
    variants: [
      { label: 'Капли для приема внутрь · 25 мл', dosage: 'капли · 25 мл', form: 'капли' },
      { label: 'Таблетки · 20 шт.', dosage: 'таблетки · 20 шт.', form: 'таблетки' },
    ],
  },
  {
    id: 'cat_46',
    name: 'Амоксициллин (Амоксиклав)',
    category: 'Антибиотики',
    tags: ['антибиотик', 'ангина', 'бактериальная инфекция', 'отит'],
    status: 'rx',
    expiry: futureDate(24),
    iconColor: '#EBF5FB',
    variants: [
      { label: 'Капсулы 500 мг · 16 шт.', dosage: '500 мг · 16 шт.', form: 'капсулы' },
      { label: 'Таблетки дисперг. 500+125 мг · 14 шт.', dosage: '625 мг · 14 шт.', form: 'таблетки' },
    ],
  },
];

function formatDateRu(iso) {
  if (!iso) return '—';
  const parts = String(iso).split('-');
  return parts.length === 3 ? `${parts[2]}.${parts[1]}.${parts[0]}` : iso;
}

function isDateExpired(iso) {
  if (!iso) return false;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return false;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return d < today;
}

export class Catalog {
  constructor(containerElement, onCustomAddClick) {
    this.container = containerElement;
    this.onCustomAddClick = onCustomAddClick;
    this.activeCategory = 'Все';
    this.searchQuery = '';
    this.categories = [
      'Все',
      'Обезболивающие',
      'Простуда и грипп',
      'Горло и кашель',
      'Нос и глаза',
      'ЖКТ и пищеварение',
      'Спазмолитики',
      'Аллергия',
      'Антисептики и кожа',
      'Сердце и давление',
      'Антибиотики',
    ];
    this.customConfigs = new Map(); // id -> { variantIdx, expiry, quantity }

    this.render();
    this.attachEvents();

    store.subscribe('kit:updated', () => this.updateCardButtons());
  }

  getMedConfig(med) {
    if (!this.customConfigs.has(med.id)) {
      this.customConfigs.set(med.id, {
        variantIdx: 0,
        expiry: med.expiry,
        quantity: 1,
      });
    }
    return this.customConfigs.get(med.id);
  }

  findExistingKitMatch(med, variant) {
    const state = store.getState();
    const lowName = med.name.toLowerCase();
    const lowDosage = variant.dosage.toLowerCase();
    return state.kitItems.find(
      (i) => i.name.toLowerCase() === lowName && (i.dosage || '').toLowerCase() === lowDosage
    ) || state.kitItems.find((i) => i.name.toLowerCase() === lowName && med.variants.length === 1);
  }

  attachEvents() {
    const searchInput = this.container.querySelector('.catalog-search-input');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.searchQuery = e.target.value.trim().toLowerCase();
        this.renderGrid();
      });
    }

    const chipsContainer = this.container.querySelector('.category-carousel');
    if (chipsContainer) {
      chipsContainer.addEventListener('click', (e) => {
        const chip = e.target.closest('.category-chip');
        if (!chip) return;
        chipsContainer.querySelectorAll('.category-chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        this.activeCategory = chip.dataset.cat;
        this.renderGrid();
      });
    }
  }

  triggerFlyAnimation(startBtn) {
    const startRect = startBtn.getBoundingClientRect();
    const targetElement = document.querySelector('.kit-header-title') || document.querySelector('.right-kit-column');
    if (!targetElement) return;
    const targetRect = targetElement.getBoundingClientRect();

    const particle = document.createElement('div');
    particle.className = 'flying-particle';
    particle.style.left = `${startRect.left + startRect.width / 2 - 7}px`;
    particle.style.top = `${startRect.top + startRect.height / 2 - 7}px`;
    document.body.appendChild(particle);

    requestAnimationFrame(() => {
      particle.style.transform = `translate(${targetRect.left - startRect.left}px, ${targetRect.top - startRect.top}px) scale(0.6)`;
      particle.style.opacity = '0.3';
    });

    setTimeout(() => {
      particle.remove();
      targetElement.classList.add('spring-transition');
      targetElement.style.transform = 'scale(1.08)';
      setTimeout(() => {
        targetElement.style.transform = 'scale(1)';
      }, 250);
    }, 650);
  }

  async handleToggleMedicine(med, btn) {
    const cfg = this.getMedConfig(med);
    const variant = med.variants[cfg.variantIdx] || med.variants[0];
    const existing = this.findExistingKitMatch(med, variant);

    if (existing) {
      await kitApi.deleteItem(existing.id);
      store.removeKitItem(existing.id);
      this.updateCardButtons();
      return;
    }

    this.triggerFlyAnimation(btn);

    const newItem = {
      id: `kit_${Date.now()}`,
      name: med.name,
      dosage: variant.dosage,
      form: variant.form,
      category: med.category,
      tags: Array.isArray(med.tags) ? med.tags : [],
      quantity: Math.max(1, Number.parseInt(cfg.quantity, 10) || 1),
      status: med.status === 'rx' || med.isPrescription ? 'rx' : 'otc',
      expiry: cfg.expiry || med.expiry,
    };

    const saved = await kitApi.addItem(newItem);
    store.addKitItem(saved && saved.id ? saved : newItem);
    store.setMascotState('happy');
    setTimeout(() => store.setMascotState('idle'), 2500);

    this.updateCardButtons();
  }

  updateCardButtons() {
    this.container.querySelectorAll('.med-card').forEach(card => {
      const medId = card.dataset.medId;
      const med = CATALOG_DATABASE.find(m => m.id === medId);
      if (!med) return;
      const cfg = this.getMedConfig(med);
      const variant = med.variants[cfg.variantIdx] || med.variants[0];
      const inKit = Boolean(this.findExistingKitMatch(med, variant));
      const btn = card.querySelector('.med-card-add-btn');
      const inKitLabel = card.querySelector('.med-card-in-kit-label');
      if (!btn) return;
      if (inKit) {
        btn.classList.add('in-kit');
        btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
        btn.title = 'В аптечке (нажмите, чтобы убрать)';
        if (inKitLabel) inKitLabel.style.visibility = 'visible';
      } else {
        btn.classList.remove('in-kit');
        btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>`;
        btn.title = 'Добавить в аптечку';
        if (inKitLabel) inKitLabel.style.visibility = 'hidden';
      }
    });
  }

  renderGrid() {
    const grid = this.container.querySelector('.medicine-grid');
    if (!grid) return;

    const filtered = CATALOG_DATABASE.filter(item => {
      const matchCat = this.activeCategory === 'Все' || item.category === this.activeCategory;
      const matchQuery = !this.searchQuery ||
        item.name.toLowerCase().includes(this.searchQuery) ||
        item.category.toLowerCase().includes(this.searchQuery) ||
        item.tags.some(t => t.toLowerCase().includes(this.searchQuery)) ||
        item.variants.some(v => v.label.toLowerCase().includes(this.searchQuery));
      return matchCat && matchQuery;
    });

    if (!filtered.length) {
      grid.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; padding: 48px 20px; color: var(--text-muted); font-size: 14px;">По вашему запросу препаратов не найдено.</div>`;
      return;
    }

    let html = '';
    filtered.forEach((med, index) => {
      const cfg = this.getMedConfig(med);
      const variant = med.variants[cfg.variantIdx] || med.variants[0];
      const inKit = Boolean(this.findExistingKitMatch(med, variant));
      const expired = isDateExpired(cfg.expiry);
      const delay = (index % 10) * 0.025;

      html += `
        <div class="med-card" data-med-id="${med.id}" data-name="${med.name}" style="animation-delay: ${delay}s">
          <div class="med-card-visual" style="background: ${med.iconColor}">
            <div class="med-card-status-pill ${med.status}">
              ${med.status === 'otc' ? 'Без рецепта' : 'По рецепту'}
            </div>
            <div class="med-card-expiry-pill ${expired ? 'expired' : 'fresh'}">
              ${expired ? `Просрочен: ${formatDateRu(cfg.expiry)}` : `до ${formatDateRu(cfg.expiry)}`}
            </div>

            <svg class="med-card-icon-svg" viewBox="0 0 64 64" fill="none">
              <rect x="14" y="10" width="36" height="44" rx="8" fill="#FFFFFF" stroke="#00B074" stroke-width="2.5"/>
              <rect x="20" y="24" width="24" height="6" rx="3" fill="#00B074" fill-opacity="0.3"/>
              <circle cx="26" cy="38" r="4" fill="#00B074"/>
              <circle cx="38" cy="38" r="4" fill="#00B074"/>
            </svg>
          </div>

          <div class="med-card-category">${med.category}</div>
          <div class="med-card-title">${med.name}</div>

          <div class="med-card-controls">
            <select class="catalog-variant-select" data-med-id="${med.id}" title="Выберите дозировку и форму выпуска">
              ${med.variants.map((v, vIdx) => `
                <option value="${vIdx}" ${vIdx === cfg.variantIdx ? 'selected' : ''}>${v.label}</option>
              `).join('')}
            </select>

            <div class="catalog-date-qty-row">
              <label class="catalog-field-mini" title="Настройте срок годности упаковки">
                <span>Срок:</span>
                <input type="date" class="catalog-expiry-input" data-med-id="${med.id}" value="${cfg.expiry}">
              </label>
              <label class="catalog-field-mini catalog-qty-mini" title="Количество упаковок">
                <span>Шт:</span>
                <input type="number" class="catalog-qty-input" data-med-id="${med.id}" min="1" max="99" value="${cfg.quantity}">
              </label>
            </div>
          </div>

          <div class="med-card-footer">
            <div class="med-card-in-kit-label" style="visibility: ${inKit ? 'visible' : 'hidden'}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
              В аптечке
            </div>

            <button class="med-card-add-btn tap-effect ${inKit ? 'in-kit' : ''}" data-med-id="${med.id}" title="${inKit ? 'В аптечке (нажмите, чтобы убрать)' : 'Добавить в аптечку'}">
              ${inKit ?
                `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>` :
                `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>`
              }
            </button>
          </div>
        </div>
      `;
    });

    grid.innerHTML = html;

    grid.querySelectorAll('.catalog-variant-select').forEach(sel => {
      sel.addEventListener('click', (e) => e.stopPropagation());
      sel.addEventListener('change', (e) => {
        const med = CATALOG_DATABASE.find(m => m.id === sel.dataset.medId);
        if (!med) return;
        const cfg = this.getMedConfig(med);
        cfg.variantIdx = Number.parseInt(e.target.value, 10) || 0;
        this.updateCardButtons();
      });
    });

    grid.querySelectorAll('.catalog-expiry-input').forEach(inp => {
      inp.addEventListener('click', (e) => e.stopPropagation());
      inp.addEventListener('change', (e) => {
        const med = CATALOG_DATABASE.find(m => m.id === inp.dataset.medId);
        if (!med) return;
        const cfg = this.getMedConfig(med);
        cfg.expiry = e.target.value || med.expiry;
        const card = inp.closest('.med-card');
        const pill = card?.querySelector('.med-card-expiry-pill');
        if (pill) {
          const exp = isDateExpired(cfg.expiry);
          pill.classList.toggle('expired', exp);
          pill.classList.toggle('fresh', !exp);
          pill.textContent = exp ? `Просрочен: ${formatDateRu(cfg.expiry)}` : `до ${formatDateRu(cfg.expiry)}`;
        }
      });
    });

    grid.querySelectorAll('.catalog-qty-input').forEach(inp => {
      inp.addEventListener('click', (e) => e.stopPropagation());
      inp.addEventListener('change', (e) => {
        const med = CATALOG_DATABASE.find(m => m.id === inp.dataset.medId);
        if (!med) return;
        const cfg = this.getMedConfig(med);
        cfg.quantity = Math.max(1, Number.parseInt(e.target.value, 10) || 1);
      });
    });

    grid.querySelectorAll('.med-card-add-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const med = CATALOG_DATABASE.find(m => m.id === btn.dataset.medId);
        if (med) this.handleToggleMedicine(med, btn);
      });
    });

    grid.querySelectorAll('.med-card-in-kit-label').forEach(label => {
      label.addEventListener('click', (e) => {
        e.stopPropagation();
        const card = label.closest('.med-card');
        const med = CATALOG_DATABASE.find(m => m.id === card?.dataset.medId);
        const btn = card?.querySelector('.med-card-add-btn');
        if (med && btn) this.handleToggleMedicine(med, btn);
      });
    });
  }

  render() {
    this.container.innerHTML = `
      <div class="catalog-view-wrap">
        <div class="catalog-search-bar">
          <svg class="catalog-search-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <input type="text" class="catalog-search-input" placeholder="Поиск среди ${CATALOG_DATABASE.length} препаратов, симптомов или дозировок...">
        </div>

        <div class="category-carousel">
          ${this.categories.map((cat, i) => `
            <button class="category-chip tap-effect ${i === 0 ? 'active' : ''}" data-cat="${cat}">
              ${cat}
            </button>
          `).join('')}
        </div>

        <div class="medicine-grid"></div>
      </div>
    `;

    this.renderGrid();
  }
}

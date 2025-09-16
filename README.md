# Anki MC Toolkit

## Состав репозитория
- [`auto_mc_distractors/`](./auto_mc_distractors/) — генерирует варианты **на лету** на ПК.  
  Док: [`README`](./auto_mc_distractors/README.md)
- [`auto_mc_tools/`](./auto_mc_tools/) — утилиты подготовки: пишет дистракторы в поле, собирает `wordpool.txt`, тасует картинки.  
  Док: [`README`](./auto_mc_tools/README.md)

## Когда что использовать
- **Только за компьютером** → `auto_mc_distractors` (без предварительной подготовки полей).  
- **ПК + мобильные клиенты** → `auto_mc_tools` (готовит данные, а карточки рендерятся JS-ом и работают везде).  
- Можно использовать **оба**: `auto_mc_tools` для подготовки, `auto_mc_distractors` — для быстрой тренировки на ПК.

## Установка и настройка
См. инструкции в README каждого аддона:
- [`auto_mc_distractors/README.md`](./auto_mc_distractors/README.md)  
- [`auto_mc_tools/README.md`](./auto_mc_tools/README.md)

---
## Совместимость

Разрабатывалось и тестировалось на **Anki 25.07.5 (Qt6/PyQt6)**. Для веток 2.1* в коде предусмотрены совместимые пути.

---


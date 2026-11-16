# Погружение в ПИВАС

Русскоязычный визуальный атлас истории пива, пивных школ, стилей и языка этикеток. В нём можно сравнить хмелевые профили, проверить себя и открыть карточки с источниками. Готовый атлас находится в [index.html](index.html) и открывается прямо в браузере.

- [`assets/`](assets/) — данные атласа, [источники в Markdown](assets/beer-sources.md), обложка, стили и JavaScript страницы.
- [`scripts/`](scripts/) — Python CLI, генераторы HTML и PDF, предпросмотр, проверки, аудит и упаковка.
- [`reference/`](reference/) — редакционное руководство, журнал правок и исследования.

## Команды

Нужен Python 3.12 или новее. Запускайте команды из корня репозитория. Справка доступна через `python scripts/atlas.py --help` и `python scripts/atlas.py <команда> --help`.

| Команда после `python scripts/atlas.py` | Что делает | Прямой запуск |
| --- | --- | --- |
| `build` | Собирает `index.html` и манифест | `python scripts/build_atlas.py` |
| `preview` | Запускает локальный сервер на `http://127.0.0.1:4173/`. Порт можно изменить через `--port` или `BEER_PREVIEW_PORT` | `python scripts/preview_atlas.py` |
| `check` | Проверяет в Chrome страницу, навигацию и сценарии без JavaScript, затем проверяет упаковку | `python scripts/check_atlas.py`, `python scripts/check_navigation.py`, `python scripts/check_static_site.py`, `python scripts/check_release.py` |
| `audit` | Запускает Lighthouse для мобильного и настольного профилей. Отчёты сохраняются в `output/site-audits/` | `python scripts/audit_atlas.py` |
| `audit-report` | Собирает сводку `output/beer-design-audit.html` по результатам аудита | `python scripts/build_site_audit.py` |
| `package` | Собирает `output/beer-site.zip` из файлов, совпадающих с проверенными в Lighthouse | `python scripts/package_deliverables.py` |
| `pdf` | Создаёт `output/beer-atlas.pdf` и отчёт в `tmp/pdf-check.json` | `python scripts/build_pdf.py` |
| `sources` | Проверяет Markdown-каталог и выдаёт JSON. Опция `--output <путь>` сохраняет его в файл | `python scripts/read_sources.py` |

### Зависимости

- Для `check` и `pdf` установите библиотеки командой `python -m pip install -r scripts/requirements.txt`.
- Для браузерных проверок и `audit` нужен Chrome. Путь к нему можно задать через `CHROME_PATH`.
- Для `audit` установите Lighthouse CLI командой `npm install --prefix tmp/lighthouse-tools lighthouse@13.6.0` в среде с Node.js 22.19 или новее. Готовый внешний Lighthouse можно указать через `LIGHTHOUSE_PATH`. Для установки в `tmp/lighthouse-tools` путь к исполняемому файлу Node можно задать через `BEER_NODE`.
- PDF использует Arial и Georgia. По умолчанию шрифты загружаются из папки шрифтов Windows. Другую папку с `arial.ttf`, `arialbd.ttf`, `ariali.ttf` и `georgia.ttf` укажите через `--font-dir`.

После изменения сайта выполните `build → check → audit → audit-report → package`. Упаковка и сводка сверяют SHA-256 файлов с обоими отчётами Lighthouse и проверяют порог 90 во всех четырёх категориях.

### PDF из сохранённого каталога

По умолчанию Python читает текущий каталог Markdown. Для сборки из сохранённого экспорта используйте `--sources`. Путь к PDF можно задать через `--output`.

```powershell
python scripts/atlas.py sources --output tmp/beer-sources.json
python scripts/build_pdf.py --sources tmp/beer-sources.json
```

### Форматирование скриптов

Python следует PEP 8. Для скриптов используются четыре пробела, двойные кавычки, UTF-8 и LF.

```sh
uvx --from ruff==0.14.10 ruff format --config scripts/ruff.toml --check scripts
```

Чтобы применить форматирование, уберите `--check`.

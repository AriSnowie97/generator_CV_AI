# ResumeCraft — Сервіс-генератор резюме

Веб-сервіс для створення, редагування та експорту резюме у форматах **PDF** (із виділюваним текстом і коректною кирилицею) та **DOCX** з AI-підказками (Google Gemini API + безпечний mock-режим для тестів).

## Архітектура та стек

- **Frontend:** Next.js 15 (React 19, TypeScript, Tailwind CSS)
- **Backend:** Python 3.12+ / FastAPI, SQLAlchemy, Pydantic
- **База даних / Кеш / Сховище:**
  - **Production / Docker:** PostgreSQL 16 + Redis 7 + MinIO (S3-сумісне сховище) + Headless Chromium (Playwright)
  - **Локальна розробка (без Docker):** автоматичний fallback на SQLite (`resumecraft_dev.db`), локальне сховище (`backend/local_storage/`), in-memory rate limiter та системний Chrome/Edge
- **AI-помічник:** Google Gemini API (`google-genai`), щоденний ліміт (`AI_DAILY_LIMIT=10`, змінюється через `.env` або `backend/ai_runtime_config.json` без релізу), маскування PII (email/телефон не передаються в AI), відповіді виключно після підтвердження користувача.

## Реалізовані можливості MVP

1. **Лендінг та демо-редактор (`/`, `/demo`)**: опис цінності, інтерактивна галерея з 3 шаблонів, режим гостя без збереження.
2. **Автентифікація (`/register`, `/login`, `/verify-email`)**: email + пароль (хеш `scrypt`), згода на обробку персональних даних, підтвердження email, обмеження кількості спроб входу, підтримка Google OAuth.
3. **Єдиний профіль (`/profile`)**: контакти, ціль, бажана зарплата/формат, досвід (до 15), освіта, навички (до 30), мови, посилання, індикатор заповненості та валідація правил ТЗ.
4. **Редактор резюме (`/editor`)**:
   - форма зліва + живий попередній перегляд справа (адаптивний перемикач на мобільних);
   - 3 ATS-дружні шаблони (`Мінімальний`, `Класичний`, `IT`) без таблиць верстки та втрати даних;
   - перестановка блоків зі збереженням порядку;
   - автозбереження + попередження, якщо резюме довше 2 сторінок;
   - AI-варіанти для «Про себе», пунктів досвіду (`дія + результат + цифра`) та довільної правки з кнопками «Прийняти / Відхилити».
5. **Експорт та налаштування (`/settings`)**: PDF та DOCX без водяних знаків із назвою `Ім'я_Прізвище_Посада_Resume.pdf/.docx`, експорт персональних даних у JSON та повне видалення акаунта з усіма файлами.

## Швидкий запуск локально (без Docker)

### 1. Бекенд (FastAPI)

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
```

API та вбудований швидкий веб-інтерфейс доступні на `http://127.0.0.1:8000` (Swagger — на `http://127.0.0.1:8000/docs`).

Для запуску одним скриптом з кореня проєкту:

```powershell
.\start.ps1
```

### 2. Окремий фронтенд (Next.js, опціонально)

```powershell
cd frontend
npm install
npm run dev
```

Інтерфейс буде доступний на `http://localhost:3000`.

### 3. Підключення реального Gemini API (опціонально)

Скопіюйте `.env.example` у `backend/.env` та задайте:

```env
GEMINI_API_KEY=ваш_ключ_gemini
AI_MOCK_MODE=false
AI_DAILY_LIMIT=10
```

## Запуск через Docker Compose (PostgreSQL + Redis + MinIO + Chromium)

```bash
cp .env.example .env
docker compose up --build -d
```

Сервіси:
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- MinIO Console: `http://localhost:9001`

## Тестування

```powershell
cd backend
.\.venv\Scripts\pytest.exe -v
```

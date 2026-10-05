# Social Network — первое ДЗ Highload Architect

Монолитное REST-приложение: регистрация пользователя, авторизация и просмотр анкеты по ID.

## Запуск

```bash
docker compose up --build
```

После запуска документация API доступна на http://localhost:8000/docs.

## Методы

- `POST /user/register` — создать пользователя;
- `POST /login` — получить JWT по `user_id` и паролю;
- `GET /user/get/{id}` — получить анкету с Bearer-токеном.

Пароли хранятся как Argon2-хеши. SQL-запросы параметризованы. ORM не используется.


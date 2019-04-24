# Google Assistant Service plugin for mdmTerminal2
После активации перехватывает все запросы, отправляет их Google Assistant Service и проговаривает ответы.
- Активация: `включить Google`.
- Деактивация: `выключить Google`.

# Установка
- [Configure the Actions Console project and the Google account](https://developers.google.com/assistant/sdk/guides/service/python/embed/config-dev-project-and-account)
- [Register a new device model and download the client secrets file](https://developers.google.com/assistant/sdk/guides/service/python/embed/register-device)
- Для поддержки русского языка: В [консоли](https://console.actions.google.com/) `Project settings` -> `LANGUAGES` выбрать русский язык.

```
mdmTerminal2/env/bin/python -m pip install --upgrade google-auth-oauthlib[tool] google-assistant-grpc
mdmTerminal2/env/bin/google-oauthlib-tool --client-secrets path/to/client_secret_<client-id>.json --scope https://www.googleapis.com/auth/assistant-sdk-prototype --save --headless
cp ~/.config/google-oauthlib-tool/credentials.json mdmTerminal2/src/data/google_assistant_credentials.json
cd mdmTerminal2/src/plugins
git clone https://github.com/Aculeasis/mdmt2-google-assistant
```
Добавить в файл `mdmTerminal2/src/data/google_assistant_credentials.json` следующие новые ключи:
- **model_id**:  `Model ID` из Device registration.
- **project_id**: `Project ID` из Project Settings.

В результате файл `google_assistant_credentials.json` должен содержать валидный JSON со следующими ключами:
```json
{"refresh_token": "...", "token_uri": "...", "client_id": "...", "client_secret": "...", "scopes": ["..."], "project_id": "...", "model_id": "..."}
```

И перезапустить терминал.

## Настройка
Хранятся в `mdmTerminal2/src/data/google_assistant_config.json`, файл будет создан при первом запуске:
- **audio_priority**: Проигрывать аудио полученное от GAS вместо текста. По умолчанию `true`.
- **models**: Модель, список моделей или `null`. Если не `null`, плагин будет перехватывать сообщения только при активации
заданными моделями игнорируя `trigger`. По умолчанию `null`.
- **start_on**: Плагин запустится активированным. По умолчанию `false`.
- **trigger**: Если не пустая строка, плагин будет перехватывать только то что начинается с нее. Например если
`trigger: "google"`, то фразу `скажи время` обработает MajorDoMo a `google скажи время` перехватит плагин.
По умолчанию `""`. Можно использовать список фраз, например `trigger: ["google", "гугл", "печенька"]`.

# Особенности
- С `audio_priority: false` проговаривает `supplemental_display_text` предназначенный для вывода на экран.
- Возможности Google Assistant Service [ограничены](https://developers.google.com/assistant/sdk/overview#features).

# Ссылки
- [mdmTerminal2](https://github.com/Aculeasis/mdmTerminal2)
- [Google Assistant SDK for devices - Python](https://github.com/googlesamples/assistant-sdk-python)

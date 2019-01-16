# Google Assistant for [mdmTerminal2](https://github.com/Aculeasis/mdmTerminal2)
После активации перехватывает все запросы, отправляет их Google Assistant и проговаривает ответы.
- Активация: `включить Google`.
- Деактивация: `выключить Google`.

# Установка
- [Register a new device model and download the client secrets file](https://developers.google.com/assistant/sdk/guides/service/python/embed/register-device)
- Включить `Google Assistant API` для проекта.

```
mdmTerminal2/env/bin/python -m pip install --upgrade google-auth-oauthlib[tool] google-assistant-grpc
mdmTerminal2/env/bin/google-oauthlib-tool --client-secrets path/to/client_secret_<client-id>.json --scope https://www.googleapis.com/auth/assistant-sdk-prototype --save --headless
cp ~/.config/google-oauthlib-tool/credentials.json mdmTerminal2/src/data/google_assistant_credentials.json
cd mdmTerminal2/src/plugins
git clone https://github.com/Aculeasis/mdmt2-google-assistant
```
Добавить в файл `mdmTerminal2/src/data/google_assistant_credentials.json` следующие ключи:
- **model_id**:  `Model ID` из Device registration.
- **project_id**: `Project ID` из настроек проекта.

И перезапустить терминал.

### Воспроизведения аудио полученного от Google Assistant API вместо текста
Если поменять в `mdmTerminal2/src/data/google_assistant_config.json` **audio_priority** на `true`, то вместо озвучивания текста
будет воспроизводить аудио также как это делают колонки от Гугла.
После изменения нужно перезапустить терминал.

# Особенности
- Ассистент отвечает на английском, русский не поддерживается.
- Без `audio_priority` проговаривает любой полученный текст, даже если он не предназначен для этого.

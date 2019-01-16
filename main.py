# Copyright (C) 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import platform
import queue
import threading
import uuid

import google.auth.transport.grpc
import google.auth.transport.requests
import google.oauth2.credentials
from google.assistant.embedded.v1alpha2 import embedded_assistant_pb2, embedded_assistant_pb2_grpc

import logger
# from languages import LANG_CODE
from modules_manager import DynamicModule, Say, EQ, Next, ANY
from utils import FakeFP

NAME = 'google-assistant'
API = 1
CFG_RELOAD = {'settings': ('lang',)}

ASSISTANT_API_ENDPOINT = 'embeddedassistant.googleapis.com'
GA_CONFIG = 'google_assistant_config'
GA_CREDENTIALS = 'google_assistant_credentials'
DEFAULT_GRPC_DEADLINE = 60 * 3 + 5

PHRASES = {
    'enable': [['включить Google', EQ], ['включи Google', EQ]],
    'disable': [['выключить Google', EQ], ['выключи Google', EQ]],
    'start_say': 'Google Assistant включен. Для выключения скажите: \'выключить Google\'',
    'stop_say': 'Google Assistant выключен.',
    'error_say': 'Ошибка коммуникации с Google Assistant',
}


class Main(threading.Thread):
    def __init__(self, cfg, log, owner):

        self.cfg = cfg
        self.log = log
        self.own = owner

        self._queue = queue.Queue()
        self._work = False
        self.disable = True

        self._text_assistant = None

        if self._ga_init():
            self.disable = False
            super().__init__()

    def start(self):
        self._work = True
        super().start()
        self._ga_stop()

    def reload(self):
        if self._text_assistant:
            pass
            # self._text_assistant.language_code = LANG_CODE.get('IETF')

    def join(self, _=None):
        self._work = False
        self._queue.put_nowait(None)
        super().join()
        self._ga_stop()
        self.own.extract_module(self._ga_start_callback)

    def run(self):
        while self._work:
            cmd = self._queue.get()
            if cmd == 'start':
                self._ga_start()
            elif cmd == 'stop':
                self._ga_stop()

    def _ga_start_callback(self, *_):
        self._queue.put_nowait('start')
        return Say(PHRASES['start_say'])

    def _ga_start(self):
        self.own.extract_module(self._ga_start_callback)
        self.own.insert_module(DynamicModule(self._ga_assist, ANY, ''))
        self.own.insert_module(DynamicModule(self._ga_stop_callback, ANY, PHRASES['disable']))

    def _ga_stop_callback(self, *_):
        self._queue.put_nowait('stop')
        return Say(PHRASES['stop_say'])

    def _ga_stop(self):
        self.own.extract_module(self._ga_assist)
        self.own.extract_module(self._ga_stop_callback)
        self.own.insert_module(DynamicModule(self._ga_start_callback, ANY, PHRASES['enable']))

    def _ga_assist(self, _, __, phrase):
        text = None
        if self._text_assistant:
            try:
                text = self._text_assistant.assist(phrase)
            except Exception as e:
                self.log('Communication error: {}'.format(e), logger.ERROR)
                text = PHRASES['error_say']
        return Say(text) if text is not None else Next

    def _ga_init(self):
        data = self._read_ga_data()
        if data is None:
            return False

        model_id, project_id, credentials = data
        id_, model_id, audio_priority = self._get_device_config(model_id, project_id, credentials)
        if id_ is None:
            return False

        grpc_channel = self._create_grpc_channel(credentials)
        if grpc_channel is None:
            return False
        self._text_assistant = SampleTextAssistant(
            # language_code=LANG_CODE.get('IETF'),
            language_code='en-US',
            channel=grpc_channel,
            device_model_id=id_,
            device_id=model_id,
            deadline_sec=DEFAULT_GRPC_DEADLINE,
            audio_priority=audio_priority

        )
        return True

    def _create_grpc_channel(self, credentials):
        try:
            return google.auth.transport.grpc.secure_authorized_channel(
                credentials, google.auth.transport.requests.Request(), ASSISTANT_API_ENDPOINT)
        except Exception as e:
            self.log('Error creating grpc channel: {}'.format(e), logger.CRIT)
            return None

    def _read_ga_data(self):
        credentials = self.cfg.load_dict(GA_CREDENTIALS)
        if not isinstance(credentials, dict):
            self.log('Error loading credentials from \'{}\''.format(GA_CREDENTIALS), logger.CRIT)
            return None
        for key in ('project_id', 'model_id'):
            if not isinstance(credentials.get(key), str) or not credentials[key]:
                self.log('Wrong or missing \'{}\' in {}. Add this key.'.format(key, GA_CREDENTIALS), logger.CRIT)
                return None
        model_id = credentials.pop('model_id')
        project_id = credentials.pop('project_id')
        try:
            credentials = google.oauth2.credentials.Credentials(token=None, **credentials)
            credentials.refresh(google.auth.transport.requests.Request())
        except Exception as e:
            self.log('Error initialization credentials \'{}\': {}'.format(GA_CREDENTIALS, e), logger.CRIT)
            return None
        return model_id, project_id, credentials

    def _get_device_config(self, model_id: str, project_id: str, credentials):
        config = self.cfg.load_dict(GA_CONFIG)
        if isinstance(config, dict):
            try:
                return config['id'], config['model_id'], config['audio_priority']
            except KeyError as e:
                self.log('Configuration \'{}\' not loaded: {}'.format(GA_CONFIG, e), logger.WARN)
        try:
            config = registry_device(model_id, project_id, credentials)
        except RuntimeError as e:
            self.log(e, logger.CRIT)
            return None, None, None
        config['audio_priority'] = False
        self.cfg.save_dict(GA_CONFIG, config, True)
        return config['id'], config['model_id'], config['audio_priority']


class SampleTextAssistant:
    """Sample Assistant that supports text based conversations.
    Args:
      language_code: language for the conversation.
      device_model_id: identifier of the device model.
      device_id: identifier of the registered device instance.
      channel: authorized gRPC channel for connection to the
        Google Assistant API.
      deadline_sec: gRPC deadline in seconds for Google Assistant API call.
    """

    def __init__(self, language_code, device_model_id, device_id, channel, deadline_sec, audio_priority):
        self.language_code = language_code
        self.device_model_id = device_model_id
        self.device_id = device_id
        self.conversation_state = None
        # Force reset of first conversation.
        self.is_new_conversation = True
        self.assistant = embedded_assistant_pb2_grpc.EmbeddedAssistantStub(channel)
        self.deadline = deadline_sec
        self.audio_priority = audio_priority

    def assist(self, text_query):
        """Send a text request to the Assistant and playback the response.
        """
        def iter_assist_requests():
            config = embedded_assistant_pb2.AssistConfig(
                audio_out_config=embedded_assistant_pb2.AudioOutConfig(
                    encoding='MP3',
                    sample_rate_hertz=16000,
                    volume_percentage=100,
                ),
                dialog_state_in=embedded_assistant_pb2.DialogStateIn(
                    language_code=self.language_code,
                    conversation_state=self.conversation_state,
                    is_new_conversation=self.is_new_conversation,
                ),
                device_config=embedded_assistant_pb2.DeviceConfig(
                    device_id=self.device_id,
                    device_model_id=self.device_model_id,
                ),
                text_query=text_query,
            )
            # Continue current conversation with later requests.
            self.is_new_conversation = False
            req = embedded_assistant_pb2.AssistRequest(config=config)
            yield req

        text_response = None
        audio = None
        for resp in self.assistant.Assist(iter_assist_requests(), self.deadline):
            if self.audio_priority and resp.HasField('audio_out') and len(resp.audio_out.audio_data) > 0:
                if audio is None:
                    audio = FakeFP()
                audio.write(resp.audio_out.audio_data)
            if resp.dialog_state_out.conversation_state:
                conversation_state = resp.dialog_state_out.conversation_state
                self.conversation_state = conversation_state
            if resp.dialog_state_out.supplemental_display_text:
                text_response = resp.dialog_state_out.supplemental_display_text
        if audio:
            audio.close()
            return lambda : ('<google-assistant-audio><mp3>', audio, '.mp3')
        return text_response


def registry_device(model_id: str, project_id: str, credentials) -> dict:
    device_base_url = 'https://{}/v1alpha2/projects/{}/devices'.format(ASSISTANT_API_ENDPOINT, project_id)
    payload = {
        'id': '{}-{}'.format(platform.uname().node, uuid.uuid1()),
        'model_id': model_id,
        'client_type': 'SDK_SERVICE'
    }
    try:
        session = google.auth.transport.requests.AuthorizedSession(credentials)
        r = session.post(device_base_url, data=json.dumps(payload))
    except Exception as e:
        raise RuntimeError('Failed request to registry device: {}'.format(e))
    if r.status_code != 200:
        raise RuntimeError('Failed to register device: {}'.format(r.text))
    del payload['client_type']
    return payload

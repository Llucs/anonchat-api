from wrapper      import Log, Utils, Headers, Challenges, VM, IP_Info
from random       import randint, random, choice
from datetime    import timezone as _tz

try:
    from zoneinfo import ZoneInfo
    def _get_tz(name):
        try:
            return ZoneInfo(name)
        except (KeyError, TypeError):
            pass
        try:
            return ZoneInfo('UTC')
        except (KeyError, TypeError):
            pass
        return _tz.utc
except ImportError:
    def _get_tz(_name=None):
        return _tz.utc
from curl_cffi    import requests
from datetime     import datetime
from uuid         import uuid4
from json         import loads
from time         import time
from typing       import Any, Generator, Optional
from base64       import b64decode
from io import BytesIO

REQUEST_TIMEOUT = 30


class ChatGPT:

    _CHROME_VERSIONS = ["chrome146", "chrome145", "chrome142", "chrome136", "chrome133a", "chrome131", "chrome"]

    def __init__(self, proxy: str=None, cookies: dict = None) -> Any:
        session = None
        for v in ChatGPT._CHROME_VERSIONS:
            try:
                session = requests.Session(impersonate=v)
                break
            except Exception:
                continue
        if session is None:
            session = requests.Session()
        self.session: requests.session.Session = session
        self.session.headers = Headers.DEFAULT
        self.data: dict = {}

        if proxy:
            self.session.proxies = {
                "all": proxy
            }

        self.ip_info: list = IP_Info.fetch_info(self.session)
        tz_name = self.ip_info[5] if len(self.ip_info) > 5 else 'UTC'
        try:
            self.timezone_offset: int = int(datetime.now(_get_tz(tz_name)).utcoffset().total_seconds() / 60)
        except Exception:
            self.timezone_offset: int = 0
        self.reacts: list = [
            "location",
            "__reactContainer$" + self._generate_react(),
            "_reactListening" + self._generate_react(),
        ]
        self.window_keys: list = [
            "0",
            "window",
            "self",
            "document",
            "name",
            "location",
            "customElements",
            "history",
            "navigation",
            "locationbar",
            "menubar",
            "personalbar",
            "scrollbars",
            "statusbar",
            "toolbar",
            "status",
            "closed",
            "frames",
            "length",
            "top",
            "opener",
            "parent",
            "frameElement",
            "navigator",
            "origin",
            "external",
            "screen",
            "innerWidth",
            "innerHeight",
            "scrollX",
            "pageXOffset",
            "scrollY",
            "pageYOffset",
            "visualViewport",
            "screenX",
            "screenY",
            "outerWidth",
            "outerHeight",
            "devicePixelRatio",
            "event",
            "clientInformation",
            "screenLeft",
            "screenTop",
            "styleMedia",
            "onsearch",
            "trustedTypes",
            "performance",
            "onappinstalled",
            "onbeforeinstallprompt",
            "crypto",
            "indexedDB",
            "sessionStorage",
            "localStorage",
            "onbeforexrselect",
            "onabort",
            "onbeforeinput",
            "onbeforematch",
            "onbeforetoggle",
            "onblur",
            "oncancel",
            "oncanplay",
            "oncanplaythrough",
            "onchange",
            "onclick",
            "onclose",
            "oncontentvisibilityautostatechange",
            "oncontextlost",
            "oncontextmenu",
            "oncontextrestored",
            "oncuechange",
            "ondblclick",
            "ondrag",
            "ondragend",
            "ondragenter",
            "ondragleave",
            "ondragover",
            "ondragstart",
            "ondrop",
            "ondurationchange",
            "onemptied",
            "onended",
            "onerror",
            "onfocus",
            "onformdata",
            "oninput",
            "oninvalid",
            "onkeydown",
            "onkeypress",
            "onkeyup",
            "onload",
            "onloadeddata",
            "onloadedmetadata",
            "onloadstart",
            "onmousedown",
            "onmouseenter",
            "onmouseleave",
            "onmousemove",
            "onmouseout",
            "onmouseover",
            "onmouseup",
            "onmousewheel",
            "onpause",
            "onplay",
            "onplaying",
            "onprogress",
            "onratechange",
            "onreset",
            "onresize",
            "onscroll",
            "onsecuritypolicyviolation",
            "onseeked",
            "onseeking",
            "onselect",
            "onslotchange",
            "onstalled",
            "onsubmit",
            "onsuspend",
            "ontimeupdate",
            "ontoggle",
            "onvolumechange",
            "onwaiting",
            "onwebkitanimationend",
            "onwebkitanimationiteration",
            "onwebkitanimationstart",
            "onwebkittransitionend",
            "onwheel",
            "onauxclick",
            "ongotpointercapture",
            "onlostpointercapture",
            "onpointerdown",
            "onpointermove",
            "onpointerrawupdate",
            "onpointerup",
            "onpointercancel",
            "onpointerover",
            "onpointerout",
            "onpointerenter",
            "onpointerleave",
            "onselectstart",
            "onselectionchange",
            "onanimationend",
            "onanimationiteration",
            "onanimationstart",
            "ontransitionrun",
            "ontransitionstart",
            "ontransitionend",
            "ontransitioncancel",
            "onafterprint",
            "onbeforeprint",
            "onbeforeunload",
            "onhashchange",
            "onlanguagechange",
            "onmessage",
            "onmessageerror",
            "onoffline",
            "ononline",
            "onpagehide",
            "onpageshow",
            "onpopstate",
            "onrejectionhandled",
            "onstorage",
            "onunhandledrejection",
            "onunload",
            "isSecureContext",
            "crossOriginIsolated",
            "scheduler",
            "alert",
            "atob",
            "blur",
            "btoa",
            "cancelAnimationFrame",
            "cancelIdleCallback",
            "captureEvents",
            "clearInterval",
            "clearTimeout",
            "close",
            "confirm",
            "createImageBitmap",
            "fetch",
            "find",
            "focus",
            "getComputedStyle",
            "getSelection",
            "matchMedia",
            "moveBy",
            "moveTo",
            "open",
            "postMessage",
            "print",
            "prompt",
            "queueMicrotask",
            "releaseEvents",
            "reportError",
            "requestAnimationFrame",
            "requestIdleCallback",
            "resizeBy",
            "resizeTo",
            "scroll",
            "scrollBy",
            "scrollTo",
            "setInterval",
            "setTimeout",
            "stop",
            "structuredClone",
            "webkitCancelAnimationFrame",
            "webkitRequestAnimationFrame",
            "chrome",
            "caches",
            "cookieStore",
            "ondevicemotion",
            "ondeviceorientation",
            "ondeviceorientationabsolute",
            "sharedStorage",
            "documentPictureInPicture",
            "fetchLater",
            "getScreenDetails",
            "queryLocalFonts",
            "showDirectoryPicker",
            "showOpenFilePicker",
            "showSaveFilePicker",
            "originAgentCluster",
            "viewport",
            "onpageswap",
            "onpagereveal",
            "credentialless",
            "fence",
            "launchQueue",
            "speechSynthesis",
            "oncommand",
            "onscrollend",
            "onscrollsnapchange",
            "onscrollsnapchanging",
            "webkitRequestFileSystem",
            "webkitResolveLocalFileSystemURL",
            "define",
            "ethereum",
            "__oai_SSR_HTML",
            "__reactRouterContext",
            "$RC",
            "__oai_SSR_TTI",
            "__reactRouterManifest",
            "__reactRouterVersion",
            "DD_RUM",
            "__REACT_INTL_CONTEXT__",
            "regeneratorRuntime",
            "DD_LOGS",
            "__STATSIG__",
            "__mobxInstanceCount",
            "__mobxGlobals",
            "_g",
            "__reactRouterRouteModules",
            "__SEGMENT_INSPECTOR__",
            "__reactRouterDataRouter",
            "MotionIsMounted",
            "_oaiHandleSessionExpired"
        ]

        if not cookies:
            self._fetch_cookies()
        else:
            self.session.cookies.update(cookies)

    def _generate_react(self) -> str:
        n = random()
        base36 = ''
        chars = '0123456789abcdefghijklmnopqrstuvwxyz'
        x = int(n * 36**10)
        for _ in range(10):
            x, r = divmod(x, 36)
            base36 = chars[r] + base36
        return base36

    def _parse_event_stream(self, stream_data: str) -> str:
        result: list = []
        lines: list = stream_data.strip().split('\n')

        for line in lines:
            if line.startswith('data:'):

                data_str: str = line[5:].strip()

                if data_str == '[DONE]':
                    break

                try:
                    data: dict = loads(data_str)
                except Exception:
                    continue

                if isinstance(data, dict):

                    if data.get('o') == 'append' and data.get('p') == '/message/content/parts/0':

                        result.append(data.get('v', ''))

                    elif data.get('o') == 'patch' and isinstance(data.get('v'), list):

                        for op in data.get('v'):

                            if op.get('o') == 'append' and op.get('p') == '/message/content/parts/0':

                                result.append(op.get('v', ''))

                    elif 'v' in data and isinstance(data['v'], str):
                        result.append(data['v'])

        return (''.join(result)).replace("\n", "")

    def _fetch_cookies(self) -> None:

        load_site: requests.models.Response = self.session.get("https://chatgpt.com", timeout=REQUEST_TIMEOUT)
        self.session.cookies.update(load_site.cookies)

        self.data["prod"] = load_site.text.split('data-build="')[1].split('"')[0]
        self.data["device-id"] = self.session.cookies.get("oai-did")

        self.start_time: int = int(time() * 1000)
        self.sid: str = str(uuid4())

        tz_name = self.ip_info[5] if len(self.ip_info) > 5 else 'UTC'
        try:
            tz_str = datetime.now(_get_tz(tz_name)).strftime(f"%a %b %d %Y %H:%M:%S GMT%z ({datetime.now(_get_tz(tz_name)).tzname()})")
        except Exception:
            tz_str = datetime.now(_tz.utc).strftime("%a %b %d %Y %H:%M:%S GMT+0000 (UTC)")

        self.data["config"] = [
            4880,
            tz_str,
            4294705152,
            random(),
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            None,
            self.data["prod"],
            "de-DE",
            "de-DE,de,en-US,en",
            random(),
            "webkitGetUserMedia\u2212function webkitGetUserMedia() { [native code] }",
            choice(self.reacts),
            choice(self.window_keys),
            randint(800, 1400) + random(),
            self.sid,
            "",
            20,
            self.start_time
        ]

    def _get_tokens(self, process_time: int=randint(1400, 2000)) -> None:

        self.session.headers = Headers.REQUIREMENTS
        self.session.headers.update({
            'oai-client-version': self.data["prod"],
            'oai-device-id': self.data["device-id"],
        })

        p_value: str = Challenges.generate_token(self.data["config"])
        self.data["vm_token"] = p_value

        tz_name = self.ip_info[5] if len(self.ip_info) > 5 else 'UTC'
        try:
            tz_str = datetime.now(_get_tz(tz_name)).strftime(f"%a %b %d %Y %H:%M:%S GMT%z ({datetime.now(_get_tz(tz_name)).tzname()})")
        except Exception:
            tz_str = datetime.now(_tz.utc).strftime("%a %b %d %Y %H:%M:%S GMT+0000 (UTC)")

        self.data["config"] = [
            4880,
            tz_str,
            4294705152,
            random(),
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            None,
            self.data["prod"],
            "de-DE",
            "de-DE,de,en-US,en",
            random(),
            "webkitGetUserMedia\u2212function webkitGetUserMedia() { [native code] }",
            choice(self.reacts),
            choice(self.window_keys),
            process_time + random(),
            self.sid,
            "",
            20,
            self.start_time
        ]

        requirements_data: dict = {
            'p': p_value,
        }

        requirements_request: requests.models.Response = self.session.post('https://chatgpt.com/backend-anon/sentinel/chat-requirements', json=requirements_data, timeout=REQUEST_TIMEOUT)

        if requirements_request.status_code == 200:
            resp_json = requirements_request.json()
            self.data["token"] = resp_json.get("token")
            self.data["proofofwork"] = resp_json.get("proofofwork")
            turnstile = resp_json.get("turnstile", {})
            self.data["bytecode"] = turnstile.get("dx")

            if not self.data.get("token") or not self.data.get("proofofwork") or not self.data.get("bytecode"):
                raise RuntimeError("Failed to get chat requirements: incomplete response from server")
        else:
            raise RuntimeError(f"Failed to get chat requirements: HTTP {requirements_request.status_code}")

    def get_conduit(self, next: bool = False) -> str:
        self.session.headers = Headers.CONDUIT
        self.session.headers.update({
            'oai-client-version': self.data["prod"],
            'oai-device-id': self.data["device-id"],
        })

        tz_name = self.ip_info[5] if len(self.ip_info) > 5 else 'UTC'

        if not next:
            post_data: dict = {
                'action': 'next',
                'fork_from_shared_post': False,
                'parent_message_id': 'client-created-root',
                'model': 'auto',
                'timezone_offset_min': self.timezone_offset,
                'timezone': tz_name,
                'history_and_training_disabled': True,
                'conversation_mode': {
                    'kind': 'primary_assistant',
                },
                'system_hints': [],
                'supports_buffering': True,
                'supported_encodings': [
                    'v1',
                ],
            }

        else:
            post_data: dict = {
                'action': 'next',
                'fork_from_shared_post': False,
                'conversation_id': self.data.get("conversation_id", ""),
                'parent_message_id': self.data.get("parent_message_id", ""),
                'model': 'auto',
                'timezone_offset_min': self.timezone_offset,
                'timezone': tz_name,
                'history_and_training_disabled': True,
                'conversation_mode': {
                    'kind': 'primary_assistant',
                },
                'system_hints': [],
                'supports_buffering': True,
                'supported_encodings': [
                    'v1',
                ],
            }

        conduit_request: requests.models.Response = self.session.post('https://chatgpt.com/backend-anon/f/conversation/prepare', json=post_data, timeout=REQUEST_TIMEOUT)

        if '"status":"ok"' in conduit_request.text:
            return conduit_request.json().get("conduit_token", "")

        else:
            error_text = conduit_request.text[:200]
            raise RuntimeError(f"Failed to get conduit token: {error_text}")

    def start_conversation(self, message: str) -> None:

        self._get_tokens()
        conduit_token: str = self.get_conduit()

        time_1: int = randint(6000, 9000)
        proof_token: str = Challenges.solve_pow(self.data["proofofwork"]["seed"], self.data["proofofwork"]["difficulty"], self.data["config"])
        if not proof_token:
            raise RuntimeError("Failed to solve Proof-of-Work challenge")
        Log.Success(f"Solved POW: {proof_token[:20]}...")
        turnstile_token: str = VM.get_turnstile(self.data["bytecode"], self.data["vm_token"], str(self.ip_info[:-1]))

        tz_name = self.ip_info[5] if len(self.ip_info) > 5 else 'UTC'

        self.session.headers = Headers.CONVERSATION
        self.session.headers.update({
            'oai-client-version': self.data["prod"],
            'oai-device-id': self.data["device-id"],
            'oai-echo-logs': f'0,{time_1},1,{time_1 + randint(1000, 1200)}',
            'openai-sentinel-chat-requirements-token': self.data["token"],
            'openai-sentinel-proof-token': proof_token,
            'openai-sentinel-turnstile-token': turnstile_token,
            'x-conduit-token': conduit_token,
        })

        conversation_data: dict = {
            'action': 'next',
            'messages': [
                {
                    'id': str(uuid4()),
                    'author': {
                        'role': 'user',
                    },
                    'create_time': round(time(), 3),
                    'content': {
                        'content_type': 'text',
                        'parts': [
                            message,
                        ],
                    },
                    'metadata': {
                        'selected_github_repos': [],
                        'selected_all_github_repos': False,
                        'serialization_metadata': {
                            'custom_symbol_offsets': [],
                        },
                    },
                },
            ],
            'parent_message_id': 'client-created-root',
            'model': 'auto',
            'timezone_offset_min': self.timezone_offset,
            'timezone': tz_name,
            'history_and_training_disabled': True,
            'conversation_mode': {
                'kind': 'primary_assistant',
            },
            'enable_message_followups': True,
            'system_hints': [],
            'supports_buffering': True,
            'supported_encodings': [
                'v1',
            ],
            'client_contextual_info': {
                'is_dark_mode': True,
                'time_since_loaded': randint(3, 6),
                'page_height': 1219,
                'page_width': 3440,
                'pixel_ratio': 1,
                'screen_height': 1440,
                'screen_width': 3440,
            },
            'paragen_cot_summary_display_override': 'allow',
            'force_parallel_switch': 'auto',
        }

        conversation_request: requests.models.Response = self.session.post('https://chatgpt.com/backend-anon/f/conversation', json=conversation_data, timeout=REQUEST_TIMEOUT)
        self.session.cookies.update(conversation_request.cookies)

        if 'Unusual activity' in conversation_request.text:
            Log.Error("Your IP got flagged by chatgpt, retry with a new IP")
            raise SystemExit(conversation_request.status_code)

        try:
            self.data["conversation_id"] = Utils.between(conversation_request.text, '"conversation_id": "', '"')
            self.data["parent_message_id"] = Utils.between(conversation_request.text, '"message_id": "', '"')
        except (IndexError, AttributeError):
            pass
        self.response = self._parse_event_stream(conversation_request.text)

    def upload_image(self, image: str) -> None:

        self.session.headers = Headers.REQUIREMENTS
        self.session.headers.update({
            'oai-client-version': self.data["prod"],
            'oai-device-id': self.data["device-id"],
        })

        self.file_name: str = str(uuid4())

        if image.startswith("data:image"):
            image = image.split(",")[1]

        try:
            raw_image = b64decode(image)
        except Exception as e:
            raise ValueError(f"Invalid base64 image data: {e}")

        self.file_size: int = len(raw_image)
        max_size = 20 * 1024 * 1024
        if self.file_size > max_size:
            raise ValueError(f"Image too large: {self.file_size} bytes (max {max_size})")
        from PIL import Image
        self.width, self.height = Image.open(BytesIO(raw_image)).size

        image_data: dict = {
            'file_name': f'{self.file_name}.png',
            'file_size': self.file_size,
            'use_case': 'multimodal',
            'timezone_offset_min': self.timezone_offset,
            'reset_rate_limits': False,
        }
        file_request: requests.models.Response = self.session.post('https://chatgpt.com/backend-anon/files', json=image_data, timeout=REQUEST_TIMEOUT)

        resp_json = file_request.json()
        self.data["file_id"] = resp_json.get("file_id")
        upload_url: str = resp_json.get("upload_url")

        if not self.data.get("file_id") or not upload_url:
            raise RuntimeError("Failed to get file upload URL from server")

        self.session.headers = Headers.FILE
        upload_request: requests.models.Response = self.session.put(upload_url, data=raw_image, timeout=REQUEST_TIMEOUT)

        self.session.headers = Headers.REQUIREMENTS
        self.session.headers.update({
            'oai-client-version': self.data["prod"],
            'oai-device-id': self.data["device-id"],
        })

        process_data: dict = {
            'file_id': self.data["file_id"],
            'use_case': 'multimodal',
            'index_for_retrieval': False,
            'file_name': f'{self.file_name}.png',
        }

        process_request: requests.models.Response = self.session.post('https://chatgpt.com/backend-anon/files/process_upload_stream', json=process_data, timeout=REQUEST_TIMEOUT)

        if "Succeeded processing " not in process_request.text:
            Log.Error("Something went wrong while uploading image")

    def start_with_image(self, message: str, image: str) -> None:

        self._get_tokens()
        conduit_token: str = self.get_conduit()
        self.upload_image(image)

        time_1: int = randint(6000, 9000)
        proof_token: str = Challenges.solve_pow(self.data["proofofwork"]["seed"], self.data["proofofwork"]["difficulty"], self.data["config"])
        if not proof_token:
            raise RuntimeError("Failed to solve Proof-of-Work for image conversation")

        turnstile_token: str = VM.get_turnstile(self.data["bytecode"], self.data["vm_token"], str(self.ip_info[:-1]))

        tz_name = self.ip_info[5] if len(self.ip_info) > 5 else 'UTC'

        self.session.headers = Headers.CONVERSATION
        self.session.headers.update({
            'oai-client-version': self.data["prod"],
            'oai-device-id': self.data["device-id"],
            'oai-echo-logs': f'0,{time_1},1,{time_1 + randint(1000, 1200)}',
            'openai-sentinel-chat-requirements-token': self.data["token"],
            'openai-sentinel-proof-token': proof_token,
            'openai-sentinel-turnstile-token': turnstile_token,
            'x-conduit-token': conduit_token,
        })

        conversation_data: dict = {
            'action': 'next',
            'messages': [
                {
                    'id': str(uuid4()),
                    'author': {
                        'role': 'user',
                    },
                    'create_time': round(time(), 3),
                    'content': {
                        'content_type': 'multimodal_text',
                        'parts': [
                            {
                                'content_type': 'image_asset_pointer',
                                'asset_pointer': f'file-service://{self.data["file_id"]}',
                                'size_bytes': self.file_size,
                                'width': self.width,
                                'height': self.height,
                            },
                            message,
                        ],
                    },
                    'metadata': {
                        'attachments': [
                            {
                                'id': self.data["file_id"],
                                'size': self.file_size,
                                'name': f'{self.file_name}.png',
                                'mime_type': 'image/png',
                                'width': self.width,
                                'height': self.height,
                                'source': 'local',
                            },
                        ],
                        'selected_github_repos': [],
                        'selected_all_github_repos': False,
                        'serialization_metadata': {
                            'custom_symbol_offsets': [],
                        },
                    },
                },
            ],
            'parent_message_id': 'client-created-root',
            'model': 'auto',
            'timezone_offset_min': self.timezone_offset,
            'timezone': tz_name,
            'history_and_training_disabled': True,
            'conversation_mode': {
                'kind': 'primary_assistant',
            },
            'enable_message_followups': True,
            'system_hints': [],
            'supports_buffering': True,
            'supported_encodings': [
                'v1',
            ],
            'client_contextual_info': {
                'is_dark_mode': True,
                'time_since_loaded': randint(3, 6),
                'page_height': 1219,
                'page_width': 3440,
                'pixel_ratio': 1,
                'screen_height': 1440,
                'screen_width': 3440,
            },
            'paragen_cot_summary_display_override': 'allow',
            'force_parallel_switch': 'auto',
        }

        conversation_request: requests.models.Response = self.session.post('https://chatgpt.com/backend-anon/f/conversation', json=conversation_data, timeout=REQUEST_TIMEOUT)
        self.session.cookies.update(conversation_request.cookies)

        if 'Unusual activity' in conversation_request.text:
            Log.Error("Your IP got flagged by chatgpt, retry with a new IP")
            raise SystemExit(conversation_request.status_code)

        try:
            self.data["conversation_id"] = Utils.between(conversation_request.text, '"conversation_id": "', '"')
            self.data["parent_message_id"] = Utils.between(conversation_request.text, '"message_id": "', '"')
        except (IndexError, AttributeError):
            pass
        self.response = self._parse_event_stream(conversation_request.text)

    def hold_conversation(self, message: str, new: bool = True) -> None:
        self.index = 2000

        if new:
            self.start_conversation(message)

        conduit_token: str = self.get_conduit(next=True)

        self._get_tokens(randint(self.index, self.index + 1000))
        self.index += 3000

        time_1: int = randint(self.index, self.index + 3000)
        proof_token: str = Challenges.solve_pow(self.data["proofofwork"]["seed"], self.data["proofofwork"]["difficulty"], self.data["config"])
        if not proof_token:
            raise RuntimeError("Failed to solve Proof-of-Work for follow-up")

        turnstile_token: str = VM.get_turnstile(self.data["bytecode"], self.data["vm_token"], str(self.ip_info[:-1]))

        tz_name = self.ip_info[5] if len(self.ip_info) > 5 else 'UTC'

        self.session.headers = Headers.CONVERSATION
        self.session.headers.update({
            'oai-client-version': self.data["prod"],
            'oai-device-id': self.data["device-id"],
            'oai-echo-logs': f'0,{time_1},1,{time_1 + randint(1000, 1200)}',
            'openai-sentinel-chat-requirements-token': self.data["token"],
            'openai-sentinel-proof-token': proof_token,
            'openai-sentinel-turnstile-token': turnstile_token,
            'x-conduit-token': conduit_token,
        })

        if new:
            new_message: str = input("Prompt: ")
        else:
            new_message: str = message

        conversation_data: dict = {
            'action': 'next',
            'messages': [
                {
                    'id': str(uuid4()),
                    'author': {
                        'role': 'user',
                    },
                    'create_time': round(time(), 3),
                    'content': {
                        'content_type': 'text',
                        'parts': [
                            new_message,
                        ],
                    },
                    'metadata': {
                        'selected_github_repos': [],
                        'selected_all_github_repos': False,
                        'serialization_metadata': {
                            'custom_symbol_offsets': [],
                        },
                    },
                },
            ],
            'conversation_id': self.data.get("conversation_id", ""),
            'parent_message_id': self.data.get("parent_message_id", ""),
            'model': 'auto',
            'timezone_offset_min': self.timezone_offset,
            'timezone': tz_name,
            'history_and_training_disabled': True,
            'conversation_mode': {
                'kind': 'primary_assistant',
            },
            'enable_message_followups': True,
            'system_hints': [],
            'supports_buffering': True,
            'supported_encodings': [
                'v1',
            ],
            'client_contextual_info': {
                'is_dark_mode': True,
                'time_since_loaded': 17,
                'page_height': 1219,
                'page_width': 3440,
                'pixel_ratio': 1,
                'screen_height': 1440,
                'screen_width': 3440,
            },
            'paragen_cot_summary_display_override': 'allow',
            'force_parallel_switch': 'auto',
        }

        conversation_request: requests.models.Response = self.session.post('https://chatgpt.com/backend-anon/f/conversation', json=conversation_data, timeout=REQUEST_TIMEOUT)
        self.session.cookies.update(conversation_request.cookies)

        if 'Unusual activity' in conversation_request.text:
            Log.Error("Your IP got flagged by chatgpt, retry with a new IP")
            raise SystemExit(conversation_request.status_code)

        try:
            self.data["conversation_id"] = Utils.between(conversation_request.text, '"conversation_id": "', '"')
            self.data["parent_message_id"] = Utils.between(conversation_request.text, '"message_id": "', '"')
        except (IndexError, AttributeError):
            pass

        self.response = self._parse_event_stream(conversation_request.text)

    def ask_question(self, message: str, image: str = None) -> str:

        if not image:
            self.start_conversation(message)
        else:
            self.start_with_image(message, image)

        return self.response

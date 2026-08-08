from wrapper      import Log, Utils, Headers, Challenges, VM, IP_Info
from random       import randint, random, choice
from datetime    import timezone as _tz
import re

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
from typing       import Any
from collections.abc import Generator
from base64       import b64decode
from io import BytesIO
from engine.text  import TextAssembler

REQUEST_TIMEOUT = 30

CHROME_UA = {
    "chrome146": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                 "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    "chrome145": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                 "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "chrome142": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                 "(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
    "chrome136": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                 "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "chrome133a": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "chrome131": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                 "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "chrome": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}


class ChatGPT:

    _CHROME_VERSIONS = ["chrome146", "chrome145", "chrome142", "chrome136", "chrome133a", "chrome131", "chrome"]

    def __init__(self, proxy: str=None, cookies: dict = None) -> Any:
        session = None
        impersonate = None
        for v in ChatGPT._CHROME_VERSIONS:
            try:
                session = requests.Session(impersonate=v)
                impersonate = v
                break
            except Exception:
                continue
        if session is None:
            session = requests.Session()
        self.session: requests.session.Session = session
        self.impersonate: str = impersonate
        self.session.headers = dict(Headers.DEFAULT)
        self.data: dict = {}
        self.chat_params: dict = {}

        if proxy:
            self.session.proxies = {
                "all": proxy
            }

        # Randomized, per-session browser metrics (previously hardcoded).
        self.browser_metrics = {
            'is_dark_mode': choice([True, False, True]),
            'time_since_loaded': randint(3, 6),
            'page_height': randint(800, 1400),
            'page_width': randint(1080, 2560),
            'pixel_ratio': round(choice([1.0, 1.25, 1.5, 2.0]), 2),
            'screen_height': randint(700, 1600),
            'screen_width': randint(1024, 3440),
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

    def _ua(self) -> str:
        return CHROME_UA.get(self.impersonate, CHROME_UA["chrome131"])

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

    def _tz_string(self, tz_name: str) -> str:
        try:
            tz_obj = datetime.now(_get_tz(tz_name))
            return tz_obj.strftime(f"%a %b %d %Y %H:%M:%S GMT%z ({tz_obj.tzname()})")
        except Exception:
            return datetime.now(_tz.utc).strftime("%a %b %d %Y %H:%M:%S GMT+0000 (UTC)")

    def _fetch_cookies(self) -> None:

        load_site: requests.models.Response = self.session.get("https://chatgpt.com", timeout=REQUEST_TIMEOUT)
        self.session.cookies.update(load_site.cookies)

        build_match = re.search(r'data-build="([^"]+)"', load_site.text)
        if not build_match:
            self.data["prod"] = ""
            if load_site.status_code >= 400:
                raise RuntimeError(f"Failed to load chatgpt.com: HTTP {load_site.status_code}")
            raise RuntimeError("Failed to locate data-build attribute on chatgpt.com")
        self.data["prod"] = build_match.group(1)
        self.data["device-id"] = self.session.cookies.get("oai-did")

        self.start_time: int = int(time() * 1000)
        self.sid: str = str(uuid4())

        tz_name = self.ip_info[5] if len(self.ip_info) > 5 else 'UTC'
        tz_str = self._tz_string(tz_name)

        self.data["config"] = [
            4880,
            tz_str,
            4294705152,
            random(),
            self._ua(),
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

        self.session.headers = dict(Headers.REQUIREMENTS)
        self.session.headers.update({
            'oai-client-version': self.data["prod"],
            'oai-device-id': self.data["device-id"],
        })

        p_value: str = Challenges.generate_token(self.data["config"])
        self.data["vm_token"] = p_value

        tz_name = self.ip_info[5] if len(self.ip_info) > 5 else 'UTC'
        tz_str = self._tz_string(tz_name)

        self.data["config"] = [
            4880,
            tz_str,
            4294705152,
            random(),
            self._ua(),
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

        requirements_request: requests.models.Response = self.session.post(
            'https://chatgpt.com/backend-anon/sentinel/chat-requirements',
            json=requirements_data,
            timeout=REQUEST_TIMEOUT,
        )

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
        self.session.headers = dict(Headers.CONDUIT)
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
                'model': getattr(self, '_requested_model', 'auto') or 'auto',
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

        conduit_request: requests.models.Response = self.session.post(
            'https://chatgpt.com/backend-anon/f/conversation/prepare',
            json=post_data,
            timeout=REQUEST_TIMEOUT,
        )

        if '"status":"ok"' in conduit_request.text:
            return conduit_request.json().get("conduit_token", "")

        else:
            error_text = conduit_request.text[:200]
            raise RuntimeError(f"Failed to get conduit token: {error_text}")

    def start_conversation(self, message: str) -> None:

        self._get_tokens()
        conduit_token: str = self.get_conduit()

        time_1: int = randint(6000, 9000)
        proof_token: str = Challenges.solve_pow(
                self.data["proofofwork"]["seed"],
                self.data["proofofwork"]["difficulty"],
                self.data["config"],
            )
        if not proof_token:
            raise RuntimeError("Failed to solve Proof-of-Work challenge")
        Log.Success(f"Solved POW: {proof_token[:20]}...")
        turnstile_token: str = VM.get_turnstile(self.data["bytecode"], self.data["vm_token"], str(self.ip_info[:-1]))

        tz_name = self.ip_info[5] if len(self.ip_info) > 5 else 'UTC'

        self.session.headers = dict(Headers.CONVERSATION)
        self.session.headers.update({
            'oai-client-version': self.data["prod"],
            'oai-device-id': self.data["device-id"],
            'oai-echo-logs': f'0,{time_1},1,{time_1 + randint(1000, 1200)}',
            'openai-sentinel-chat-requirements-token': self.data["token"],
            'openai-sentinel-proof-token': proof_token,
            'openai-sentinel-turnstile-token': turnstile_token,
            'x-conduit-token': conduit_token,
        })

        conversation_data: dict = self._build_payload(message, tz_name)

        conversation_request: requests.models.Response = self.session.post(
            'https://chatgpt.com/backend-anon/f/conversation',
            json=conversation_data,
            timeout=REQUEST_TIMEOUT,
        )
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

        self.session.headers = dict(Headers.REQUIREMENTS)
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
            raise ValueError(f"Invalid base64 image data: {e}") from e

        self.file_size: int = len(raw_image)
        max_size = 20 * 1024 * 1024
        if self.file_size > max_size:
            raise ValueError(f"Image too large: {self.file_size} bytes (max {max_size})")
        from PIL import Image
        try:
            with Image.open(BytesIO(raw_image)) as img:
                self.width, self.height = img.size
                fmt = (img.format or 'PNG').lower()
        except Exception as e:
            raise ValueError(f"Invalid image data: {e}") from e
        mime_map = {
            'png': 'image/png', 'jpeg': 'image/jpeg', 'jpg': 'image/jpeg',
            'gif': 'image/gif', 'webp': 'image/webp', 'bmp': 'image/bmp',
        }
        self.mime_type: str = mime_map.get(fmt, 'image/png')
        self.file_ext: str = 'jpeg' if fmt == 'jpg' else fmt

        image_data: dict = {
            'file_name': f'{self.file_name}.{self.file_ext}',
            'file_size': self.file_size,
            'use_case': 'multimodal',
            'timezone_offset_min': self.timezone_offset,
            'reset_rate_limits': False,
        }
        file_request: requests.models.Response = self.session.post(
            'https://chatgpt.com/backend-anon/files',
            json=image_data,
            timeout=REQUEST_TIMEOUT,
        )

        resp_json = file_request.json()
        self.data["file_id"] = resp_json.get("file_id")
        upload_url: str = resp_json.get("upload_url")

        if not self.data.get("file_id") or not upload_url:
            raise RuntimeError("Failed to get file upload URL from server")

        self.session.headers = dict(Headers.FILE)
        self.session.headers['content-type'] = self.mime_type
        upload_request: requests.models.Response = self.session.put(upload_url, data=raw_image, timeout=REQUEST_TIMEOUT)
        if upload_request.status_code >= 400:
            raise RuntimeError(f"File upload failed: HTTP {upload_request.status_code}")

        self.session.headers = dict(Headers.REQUIREMENTS)
        self.session.headers.update({
            'oai-client-version': self.data["prod"],
            'oai-device-id': self.data["device-id"],
        })

        process_data: dict = {
            'file_id': self.data["file_id"],
            'use_case': 'multimodal',
            'index_for_retrieval': False,
            'file_name': f'{self.file_name}.{self.file_ext}',
        }

        process_request: requests.models.Response = self.session.post(
            'https://chatgpt.com/backend-anon/files/process_upload_stream',
            json=process_data,
            timeout=REQUEST_TIMEOUT,
        )

        if "Succeeded processing " not in process_request.text:
            Log.Error("Something went wrong while uploading image")

    def start_with_image(self, message: str, image: str) -> None:

        self._get_tokens()
        conduit_token: str = self.get_conduit()
        self.upload_image(image)

        time_1: int = randint(6000, 9000)
        proof_token: str = Challenges.solve_pow(
                self.data["proofofwork"]["seed"],
                self.data["proofofwork"]["difficulty"],
                self.data["config"],
            )
        if not proof_token:
            raise RuntimeError("Failed to solve Proof-of-Work for image conversation")

        turnstile_token: str = VM.get_turnstile(self.data["bytecode"], self.data["vm_token"], str(self.ip_info[:-1]))

        tz_name = self.ip_info[5] if len(self.ip_info) > 5 else 'UTC'

        self.session.headers = dict(Headers.CONVERSATION)
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
                                'name': f'{self.file_name}.{self.file_ext}',
                                'mime_type': self.mime_type,
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
                'is_dark_mode': self.browser_metrics['is_dark_mode'],
                'time_since_loaded': self.browser_metrics['time_since_loaded'],
                'page_height': self.browser_metrics['page_height'],
                'page_width': self.browser_metrics['page_width'],
                'pixel_ratio': self.browser_metrics['pixel_ratio'],
                'screen_height': self.browser_metrics['screen_height'],
                'screen_width': self.browser_metrics['screen_width'],
            },
            'paragen_cot_summary_display_override': 'allow',
            'force_parallel_switch': 'auto',
        }

        conversation_request: requests.models.Response = self.session.post(
            'https://chatgpt.com/backend-anon/f/conversation',
            json=conversation_data,
            timeout=REQUEST_TIMEOUT,
        )
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
        proof_token: str = Challenges.solve_pow(
                self.data["proofofwork"]["seed"],
                self.data["proofofwork"]["difficulty"],
                self.data["config"],
            )
        if not proof_token:
            raise RuntimeError("Failed to solve Proof-of-Work for follow-up")

        turnstile_token: str = VM.get_turnstile(self.data["bytecode"], self.data["vm_token"], str(self.ip_info[:-1]))

        tz_name = self.ip_info[5] if len(self.ip_info) > 5 else 'UTC'

        self.session.headers = dict(Headers.CONVERSATION)
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
            new_message: str = message

        conversation_data: dict = self._build_payload(
            new_message,
            tz_name,
            parent_message_id=self.data.get("parent_message_id", ""),
        )

        conversation_request: requests.models.Response = self.session.post(
            'https://chatgpt.com/backend-anon/f/conversation',
            json=conversation_data,
            timeout=REQUEST_TIMEOUT,
        )
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

    def _stream_sse(self, response) -> Generator[str, None, None]:
        seen_assistant = False
        assem = TextAssembler()
        for line in response.iter_lines():
            if not line:
                continue
            if isinstance(line, bytes):
                line = line.decode('utf-8', errors='replace')
            if not line.startswith('data:'):
                continue
            data_str = line[5:].strip()
            if data_str == '[DONE]':
                break
            try:
                data = loads(data_str)
            except Exception:
                continue
            if not isinstance(data, dict):
                continue

            t = data.get('type')
            if t == 'server_ste_metadata':
                m = data.get('metadata', {})
                if hasattr(self, 'model_slug'):
                    self.model_slug = m.get('model_slug')
            if t == 'conversation_detail_metadata':
                if hasattr(self, 'rate_limits'):
                    self.rate_limits = data.get('limits_progress')
            if t == 'resume_conversation_token':
                if hasattr(self, 'resume_token'):
                    self.resume_token = data.get('token')

            if data.get('o') == 'patch' and isinstance(data.get('v'), list):
                for op in data.get('v'):
                    if op.get('p') == '/message/metadata':
                        meta = op.get('v', {})
                        if hasattr(self, 'model_slug') and meta.get('resolved_model_slug'):
                            self.model_slug = meta.get('resolved_model_slug')

            v = data.get('v', {})
            if isinstance(v, dict):
                msg = v.get('message', {})
                if isinstance(msg, dict):
                    role = msg.get('author', {}).get('role')
                    if role == 'assistant':
                        seen_assistant = True
                        initial = msg.get('content', {}).get('parts', [])
                        if initial and isinstance(initial[0], str):
                            assem.absorb(initial[0], full_snapshot=True)
                            emitted = assem.suffix()
                            if emitted:
                                yield emitted
                        mid = msg.get('id')
                        if mid and hasattr(self, 'message_id'):
                            self.message_id = mid

            emitted = None
            if data.get('o') == 'append' and data.get('p') == '/message/content/parts/0':
                chunk = data.get('v', '')
                if isinstance(chunk, str):
                    assem.absorb(chunk)
                    emitted = assem.suffix()
            elif data.get('o') == 'patch' and isinstance(data.get('v'), list) and seen_assistant:
                for op in data.get('v'):
                    if op.get('o') == 'append' and op.get('p') == '/message/content/parts/0':
                        chunk = op.get('v', '')
                        if isinstance(chunk, str):
                            assem.absorb(chunk)
                            emitted = assem.suffix()
            elif 'v' in data and isinstance(data['v'], str) and seen_assistant:
                chunk = data['v']
                if re.fullmatch(r'[\w-]{30,}', chunk):
                    continue
                assem.absorb(chunk)
                emitted = assem.suffix()

            if emitted:
                yield emitted

    def start_conversation_stream(self, message: str, tools: list = None,
                                  tool_choice: str = None) -> Generator[str, None, None]:
        self._get_tokens()
        conduit_token: str = self.get_conduit()

        time_1: int = randint(6000, 9000)
        proof_token: str = Challenges.solve_pow(
            self.data["proofofwork"]["seed"],
            self.data["proofofwork"]["difficulty"],
            self.data["config"]
        )
        if not proof_token:
            raise RuntimeError("Failed to solve Proof-of-Work challenge")
        Log.Success(f"Solved POW: {proof_token[:20]}...")
        turnstile_token: str = VM.get_turnstile(
            self.data["bytecode"], self.data["vm_token"], str(self.ip_info[:-1])
        )

        tz_name = self.ip_info[5] if len(self.ip_info) > 5 else 'UTC'

        self.session.headers = dict(Headers.CONVERSATION)
        self.session.headers.update({
            'oai-client-version': self.data["prod"],
            'oai-device-id': self.data["device-id"],
            'oai-echo-logs': f'0,{time_1},1,{time_1 + randint(1000, 1200)}',
            'openai-sentinel-chat-requirements-token': self.data["token"],
            'openai-sentinel-proof-token': proof_token,
            'openai-sentinel-turnstile-token': turnstile_token,
            'x-conduit-token': conduit_token,
        })

        conversation_data: dict = self._build_payload(message, tz_name, tools=tools, tool_choice=tool_choice)

        response = self.session.post(
            'https://chatgpt.com/backend-anon/f/conversation',
            json=conversation_data,
            stream=True,
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code >= 400:
            msg = "Your IP got flagged by chatgpt, retry with a new IP"
            Log.Error(msg)
            if 'Unusual activity' not in response.text:
                raise RuntimeError(f"ChatGPT conversation failed: HTTP {response.status_code}")
            raise SystemExit(response.status_code)

        full_text = []
        for chunk in self._stream_sse(response):
            full_text.append(chunk)
            yield chunk

        self.response = ''.join(full_text)

    def list_models(self) -> list[dict]:
        self._fetch_cookies()
        r = self.session.get(
            'https://chatgpt.com/backend-anon/models',
            timeout=REQUEST_TIMEOUT
        )
        if r.status_code >= 400:
            return []
        data = r.json()
        return data.get('models', [])

    def _build_payload(self, message: str, tz_name: str,
                     tools: list = None, tool_choice: str = None,
                     parent_message_id: str = 'client-created-root') -> dict:
        payload: dict = {
            'action': 'next',
            'messages': [{
                'id': str(uuid4()),
                'author': {'role': 'user'},
                'create_time': round(time(), 3),
                'content': {'content_type': 'text', 'parts': [message]},
                'metadata': {
                    'selected_github_repos': [],
                    'selected_all_github_repos': False,
                    'serialization_metadata': {'custom_symbol_offsets': []},
                },
            }],
            'parent_message_id': parent_message_id,
            'model': getattr(self, '_requested_model', 'auto') or 'auto',
            'timezone_offset_min': self.timezone_offset,
            'timezone': tz_name,
            'history_and_training_disabled': True,
            'conversation_mode': {'kind': 'primary_assistant'},
            'enable_message_followups': True,
            'system_hints': [],
            'supports_buffering': True,
            'supported_encodings': ['v1'],
            'client_contextual_info': dict(self.browser_metrics),
            'paragen_cot_summary_display_override': 'allow',
            'force_parallel_switch': 'auto',
        }
        if parent_message_id != 'client-created-root':
            payload['conversation_id'] = self.data.get("conversation_id", "")
        if tools:
            payload['tools'] = tools
        if tool_choice:
            payload['tool_choice'] = tool_choice
        for k, v in getattr(self, 'chat_params', {}).items():
            if v is not None and k not in payload:
                payload[k] = v
        return payload

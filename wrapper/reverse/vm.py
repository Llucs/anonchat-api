from json        import dumps
from base64      import b64encode
from random      import randint, random
from .decompiler import Decompiler
from .parse      import Parser


class VM:

    html_object: str = dumps({"x":0,"y":1219,"width":37.8125,"height":30,"top":1219,"right":37.8125,"bottom":1249,"left":0}, separators=(',', ':'))

    @staticmethod
    def xor(e, t):
        t = str(t)
        e = str(e)
        n = ""

        for r in range(len(e)):
            n += chr(ord(e[r]) ^ ord(t[r % len(t)]))

        return n

    @staticmethod
    def get_turnstile(turnstile: str, token: str, ip_info: str) -> str:

        decompiled: str = Decompiler.decompile_vm(turnstile, token)

        xor_key, keys = Parser.parse_keys(decompiled)

        payload: dict = {}

        for key, value in keys.items():
            try:
                value = float(value)
            except (TypeError, ValueError):
                pass

            if isinstance(value, float):
                payload[key] = b64encode(VM.xor(str(value), xor_key).encode("utf-8")).decode("utf-8")

            elif "singlebtoa" in value:
                payload[key] = b64encode(value.split("singlebtoa(")[1].split(")")[0].encode("utf-8")).decode("utf-8")

            elif "doublexor" in value:
                # JS: XOR_STR(XOR_STR(x, key), key); the old code XORed the
                # number with itself, producing 0-bytes only (garbage).
                number: str = value.split("doublexor(")[1].split(")")[0]
                once: str = VM.xor(number, xor_key)
                twice: str = VM.xor(once, xor_key)
                payload[key] = b64encode(twice.encode('utf-8')).decode('utf-8')

            elif "ipinfo" in value:
                payload[key] = b64encode(VM.xor(ip_info, xor_key).encode("utf-8")).decode("utf-8")

            elif "element" in value:
                payload[key] = b64encode(VM.xor(VM.html_object, xor_key).encode()).decode()

            elif "location" in value:
                location: str = 'https://chatgpt.com/'
                payload[key] = b64encode(VM.xor(location, xor_key).encode("utf-8")).decode("utf-8")

            elif "random_1" in value:
                random_value: float = random()
                payload[key] = b64encode(VM.xor(str(random_value), xor_key).encode("utf-8")).decode("utf-8")

            elif "random_2" in value:
                payload[key] = random()

            elif "vendor" in value:
                vendor_info: str = '["Google Inc.","Win32",8,0]'
                payload[key] = b64encode(VM.xor(vendor_info, xor_key).encode("utf-8")).decode("utf-8")

            elif "localstorage" in value:
                payload[key] = b64encode(VM.xor('oai/apps/hasDismissedTeamsNoAuthUpsell,oai/apps/lastSeenNoAuthTrialsBannerAt,oai-did,oai/apps/lastSeenNoAuthTrialsBannerAt,oai/apps/noAuthGoUpsellModalDismissed,oai/apps/hasDismissedBusinessFreeTrialUpsellModal,oai/apps/capExpiresAt,statsig.session_id.1792610830,oai/apps/hasSeenNoAuthImagegenNux,oai/apps/lastPageLoadDate,client-correlated-secret,statsig.stable_id.1792610830,oai/apps/debugSettings,oai/apps/hasDismissedPlusFreeTrialUpsellModal,oai/apps/tatertotInContextUpsellBannerV2,search.attributions-settings', xor_key).encode("utf-8")).decode("utf-8")

            elif "history" in value:
                payload[key] = b64encode(VM.xor(str(randint(1, 5)), xor_key).encode()).decode()

            else:
                pass

        turnstile_token: str = b64encode(VM.xor(dumps(payload, separators=(',', ':')), xor_key).encode("utf-8")).decode("utf-8")

        return turnstile_token

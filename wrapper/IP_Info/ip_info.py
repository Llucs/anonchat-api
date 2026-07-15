from curl_cffi import requests


class IP_Info:

    @staticmethod
    def fetch_info(session: requests.session.Session) -> list:
        try:
            r = session.get('https://ipapi.co/json/', timeout=10)
            data = r.json()
            return [
                str(data.get('ip', '0.0.0.0')),
                str(data.get('city', 'Unknown')),
                str(data.get('region', 'Unknown')),
                str(data.get('latitude', '0')),
                str(data.get('longitude', '0')),
                str(data.get('timezone', 'UTC')),
            ]
        except Exception:
            return ['0.0.0.0', 'Unknown', 'Unknown', '0', '0', 'UTC']

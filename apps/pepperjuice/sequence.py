import requests
from django.conf import settings

SEQUENCE_API_BASE = getattr(settings, 'SEQUENCE_API_BASE', 'https://api.getsequence.io')


class SequenceAPIError(Exception):
    pass


class SequenceClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.session = requests.Session()
        # Legacy access tokens use x-sequence-access-token: Bearer <token>
        # New sk_ keys try Authorization: Bearer as well
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'x-sequence-access-token': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        })

    def _post(self, path, payload=None):
        url = f'{SEQUENCE_API_BASE}{path}'
        try:
            resp = self.session.post(url, json=payload or {}, timeout=15)
            if not resp.ok:
                snippet = resp.text[:300].replace('\n', ' ')
                raise SequenceAPIError(
                    f'HTTP {resp.status_code} from {url} — {snippet}'
                )
            try:
                return resp.json()
            except Exception:
                snippet = resp.text[:300].replace('\n', ' ')
                raise SequenceAPIError(f'Non-JSON response from {url}: {snippet}')
        except requests.RequestException as e:
            raise SequenceAPIError(f'Request failed for {url}: {e}') from e

    def get_accounts(self):
        return self._post('/accounts')

    def trigger_rule(self, rule_secret, amount=None):
        headers = {'x-sequence-signature': rule_secret, 'Content-Type': 'application/json'}
        payload = {}
        if amount is not None:
            payload['amount'] = str(amount)
        url = f'{SEQUENCE_API_BASE}/rules/trigger'
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            if not resp.ok:
                raise SequenceAPIError(f'Rule trigger HTTP {resp.status_code}: {resp.text[:300]}')
            return resp.json()
        except requests.RequestException as e:
            raise SequenceAPIError(f'Rule trigger request failed: {e}') from e

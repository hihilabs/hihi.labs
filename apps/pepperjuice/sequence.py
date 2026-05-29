import requests
from django.conf import settings

# Sequence uses x-sequence-access-token for balance/account reads.
# Rule triggers use per-rule x-sequence-signature secrets instead.
# Confirm the exact base URL from your API key page after creation.
SEQUENCE_API_BASE = getattr(settings, 'SEQUENCE_API_BASE', 'https://api.getsequence.io/v1')


class SequenceAPIError(Exception):
    pass


class SequenceClient:
    def __init__(self, api_key):
        self.session = requests.Session()
        self.session.headers.update({
            'x-sequence-access-token': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        })

    def _get(self, path):
        try:
            resp = self.session.get(f'{SEQUENCE_API_BASE}{path}', timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as e:
            raise SequenceAPIError(f'Sequence API error {e.response.status_code}: {e.response.text}') from e
        except requests.RequestException as e:
            raise SequenceAPIError(str(e)) from e

    def get_accounts(self):
        return self._get('/accounts')

    def trigger_rule(self, rule_secret, amount=None):
        headers = {'x-sequence-signature': rule_secret, 'Content-Type': 'application/json'}
        payload = {}
        if amount is not None:
            payload['amount'] = str(amount)
        try:
            resp = requests.post(
                f'{SEQUENCE_API_BASE}/rules/trigger',
                headers=headers,
                json=payload,
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as e:
            raise SequenceAPIError(f'Rule trigger error {e.response.status_code}: {e.response.text}') from e
        except requests.RequestException as e:
            raise SequenceAPIError(str(e)) from e

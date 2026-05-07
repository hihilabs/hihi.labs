# Module registry — add new modules here, no migrations needed.
# type:  'utility' | 'data' | 'ai' | 'infra'
# status: 'live' | 'beta' | 'wip'

MODULES = [
    {
        'slug':        'sms-autoreplier',
        'name':        'SMS AutoReplier',
        'type':        'utility',
        'icon':        'fa-message-dots',
        'color':       '#7c6af7',
        'description': 'Native Android background service — watches incoming SMS for keyword patterns and fires a configurable auto-reply in milliseconds. Built for on-call shift claiming.',
        'status':      'beta',
        'platform':    'Android',
        'live_url':    'https://expo.hihilabs.xyz',
        'source_url':  'https://expo.hihilabs.xyz/sms-autoreplier-src.tar',
        'tags':        ['android', 'kotlin', 'expo', 'sms'],
    },
    # ── add future modules below ──────────────────────────────────────────────
    # {
    #     'slug':        'my-module',
    #     'name':        'My Module',
    #     'type':        'utility',   # utility | data | ai | infra
    #     'icon':        'fa-bolt',
    #     'color':       '#2dd4bf',
    #     'description': 'One sentence.',
    #     'status':      'wip',       # live | beta | wip
    #     'platform':    'Web',
    #     'live_url':    'https://my-module.hihilabs.xyz',
    #     'source_url':  '',
    #     'tags':        ['tag1', 'tag2'],
    # },
]

"""
Run: python manage.py shell < seed.py
Seeds default template categories and prompt templates for HiHi Labs AI module.
"""
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hihilabs.settings')
django.setup()

from apps.claude_ai.models import TemplateCategory, PromptTemplate

CATEGORIES = [
    {'name': 'Client Comms', 'icon': 'fa-solid fa-envelope', 'order': 1},
    {'name': 'Proposals & Contracts', 'icon': 'fa-solid fa-file-contract', 'order': 2},
    {'name': 'Content & Copy', 'icon': 'fa-solid fa-pen-nib', 'order': 3},
    {'name': 'Dev & Tech', 'icon': 'fa-solid fa-code', 'order': 4},
    {'name': 'Business Ops', 'icon': 'fa-solid fa-briefcase', 'order': 5},
    {'name': 'Audio & Music', 'icon': 'fa-solid fa-music', 'order': 6},
]

TEMPLATES = [
    # Client Comms
    {
        'name': 'Cold Outreach Email',
        'category': 'Client Comms',
        'icon': 'fa-solid fa-paper-plane',
        'description': 'Write a professional cold email to a potential client.',
        'prompt_template': 'Write a concise, professional cold outreach email to {{recipient}} about {{service_or_project}}. Keep it under 150 words. No filler. End with a clear CTA.',
        'variables': [
            {'name': 'recipient', 'label': 'Recipient (name/company)', 'type': 'text'},
            {'name': 'service_or_project', 'label': 'Service or Project Pitch', 'type': 'textarea'},
        ],
    },
    {
        'name': 'Follow-Up Email',
        'category': 'Client Comms',
        'icon': 'fa-solid fa-reply',
        'description': 'A follow-up after a proposal, meeting, or unanswered message.',
        'prompt_template': 'Write a brief follow-up email to {{client}} regarding {{context}}. Friendly but direct. Keep it under 100 words.',
        'variables': [
            {'name': 'client', 'label': 'Client Name', 'type': 'text'},
            {'name': 'context', 'label': 'What you\'re following up on', 'type': 'textarea'},
        ],
    },
    {
        'name': 'Project Update',
        'category': 'Client Comms',
        'icon': 'fa-solid fa-circle-info',
        'description': 'Send a status update to a client in plain language.',
        'prompt_template': 'Write a client-facing project update email for {{project_name}}. Completed: {{completed}}. Next steps: {{next_steps}}. Blockers: {{blockers}}. Be clear and non-technical.',
        'variables': [
            {'name': 'project_name', 'label': 'Project Name', 'type': 'text'},
            {'name': 'completed', 'label': 'What got done', 'type': 'textarea'},
            {'name': 'next_steps', 'label': 'What\'s next', 'type': 'textarea'},
            {'name': 'blockers', 'label': 'Blockers (or "none")', 'type': 'text'},
        ],
    },
    # Proposals & Contracts
    {
        'name': 'Service Proposal',
        'category': 'Proposals & Contracts',
        'icon': 'fa-solid fa-file-alt',
        'description': 'Generate a full service proposal from bullet points.',
        'prompt_template': 'Write a professional service proposal for {{client_name}}. Project: {{project_description}}. Services: {{services}}. Timeline: {{timeline}}. Format with sections: Overview, Scope, Deliverables, Timeline, Investment.',
        'variables': [
            {'name': 'client_name', 'label': 'Client Name', 'type': 'text'},
            {'name': 'project_description', 'label': 'Project Description', 'type': 'textarea'},
            {'name': 'services', 'label': 'Services Included', 'type': 'textarea'},
            {'name': 'timeline', 'label': 'Timeline', 'type': 'text'},
        ],
        'use_smart_model': True,
    },
    {
        'name': 'Freelance Contract Outline',
        'category': 'Proposals & Contracts',
        'icon': 'fa-solid fa-file-signature',
        'description': 'Generate contract terms for a freelance project.',
        'prompt_template': 'Write a freelance contract outline for {{project_name}} with client {{client_name}}. Services: {{services}}. Rate: {{rate}}. Include: scope, payment terms, revision policy, IP ownership, kill fee clause.',
        'variables': [
            {'name': 'project_name', 'label': 'Project Name', 'type': 'text'},
            {'name': 'client_name', 'label': 'Client Name', 'type': 'text'},
            {'name': 'services', 'label': 'Services', 'type': 'textarea'},
            {'name': 'rate', 'label': 'Rate / Budget', 'type': 'text'},
        ],
        'use_smart_model': True,
    },
    # Content & Copy
    {
        'name': 'Bio / About Section',
        'category': 'Content & Copy',
        'icon': 'fa-solid fa-id-badge',
        'description': 'Write a short bio for a website, artist page, or profile.',
        'prompt_template': 'Write a short professional bio for {{name}}. They do: {{what_they_do}}. Tone: {{tone}}. Max 120 words. Third person.',
        'variables': [
            {'name': 'name', 'label': 'Name or Brand', 'type': 'text'},
            {'name': 'what_they_do', 'label': 'What they do', 'type': 'textarea'},
            {'name': 'tone', 'label': 'Tone (e.g. edgy, professional, warm)', 'type': 'text'},
        ],
    },
    {
        'name': 'Artist Press Release',
        'category': 'Content & Copy',
        'icon': 'fa-solid fa-bullhorn',
        'description': 'Draft a press release for a music release or event.',
        'prompt_template': 'Write a press release for {{artist_name}} announcing {{announcement}}. Include: hook opener, 2-3 body paragraphs, quote from artist, boilerplate about the artist. Tone: {{tone}}.',
        'variables': [
            {'name': 'artist_name', 'label': 'Artist / Act Name', 'type': 'text'},
            {'name': 'announcement', 'label': 'What\'s being announced', 'type': 'textarea'},
            {'name': 'tone', 'label': 'Tone', 'type': 'text'},
        ],
    },
    # Dev & Tech
    {
        'name': 'Django Model Plan',
        'category': 'Dev & Tech',
        'icon': 'fa-brands fa-python',
        'description': 'Describe a feature and get a Django model + view scaffold plan.',
        'prompt_template': 'I\'m building a Django feature: {{feature_description}}. Draft the models (fields, relationships, Meta, __str__), key views (list, detail, create/update), and URL patterns. Use SQLite-friendly patterns. Be concrete.',
        'variables': [
            {'name': 'feature_description', 'label': 'Feature Description', 'type': 'textarea'},
        ],
        'use_smart_model': True,
    },
    {
        'name': 'Debug This Error',
        'category': 'Dev & Tech',
        'icon': 'fa-solid fa-bug',
        'description': 'Paste an error and get a diagnosis + fix.',
        'prompt_template': 'I got this error:\n\n{{error}}\n\nContext: {{context}}\n\nDiagnose the root cause and give me the exact fix. No fluff.',
        'variables': [
            {'name': 'error', 'label': 'Error message / traceback', 'type': 'textarea'},
            {'name': 'context', 'label': 'What you were doing / relevant code snippet', 'type': 'textarea'},
        ],
    },
    {
        'name': 'SQL Query Writer',
        'category': 'Dev & Tech',
        'icon': 'fa-solid fa-database',
        'description': 'Describe what you need and get a raw SQL query.',
        'prompt_template': 'Write a MySQL query for this: {{request}}. Table context: {{tables}}. Output only the SQL, then a one-line explanation.',
        'variables': [
            {'name': 'request', 'label': 'What the query should do', 'type': 'textarea'},
            {'name': 'tables', 'label': 'Tables / schema context', 'type': 'textarea'},
        ],
    },
    # Business Ops
    {
        'name': 'Invoice Line Items',
        'category': 'Business Ops',
        'icon': 'fa-solid fa-receipt',
        'description': 'Describe work done and get clean invoice line items.',
        'prompt_template': 'Generate clear invoice line items for work done on {{project}}. Work completed: {{work_done}}. Rate: {{rate}}. Format each line as: Item | Hours | Rate | Total. Then total at the bottom.',
        'variables': [
            {'name': 'project', 'label': 'Project / Client', 'type': 'text'},
            {'name': 'work_done', 'label': 'Work completed (bullet points ok)', 'type': 'textarea'},
            {'name': 'rate', 'label': 'Hourly rate or fixed', 'type': 'text'},
        ],
    },
    {
        'name': 'Tax Write-Off Summary',
        'category': 'Business Ops',
        'icon': 'fa-solid fa-receipt',
        'description': 'Turn expense notes into a formatted write-off summary for your accountant.',
        'prompt_template': 'Turn these expenses into a clean tax write-off summary for a freelance software developer:\n\n{{expenses}}\n\nGroup by category (Software, Hardware, Home Office, Travel, Professional Services, etc.). List each item, amount, and business purpose. End with total by category.',
        'variables': [
            {'name': 'expenses', 'label': 'Expense notes (paste anything)', 'type': 'textarea'},
        ],
        'use_smart_model': True,
    },
    # Audio & Music
    {
        'name': 'Track Description',
        'category': 'Audio & Music',
        'icon': 'fa-solid fa-headphones',
        'description': 'Write a short description for a track or mix for a playlist, Soundcloud, or press kit.',
        'prompt_template': 'Write a track description for {{track_name}} by {{artist}}. Genre/vibe: {{vibe}}. Key influences or sounds: {{influences}}. Max 80 words. Evocative, not generic.',
        'variables': [
            {'name': 'track_name', 'label': 'Track / Mix Name', 'type': 'text'},
            {'name': 'artist', 'label': 'Artist Name', 'type': 'text'},
            {'name': 'vibe', 'label': 'Genre / Vibe', 'type': 'text'},
            {'name': 'influences', 'label': 'Influences or sounds', 'type': 'text'},
        ],
    },
]


for cat_data in CATEGORIES:
    cat, _ = TemplateCategory.objects.get_or_create(name=cat_data['name'], defaults=cat_data)
    print(f'  category: {cat.name}')

for tmpl_data in TEMPLATES:
    cat_name = tmpl_data.pop('category')
    cat = TemplateCategory.objects.get(name=cat_name)
    t, created = PromptTemplate.objects.get_or_create(
        name=tmpl_data['name'],
        defaults={**tmpl_data, 'category': cat},
    )
    print(f'  {"+" if created else "="} template: {t.name}')

print('\nDone.')

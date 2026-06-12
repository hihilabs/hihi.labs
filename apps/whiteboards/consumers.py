"""Room websocket — realtime whiteboard sync, transcript, presence, loyd.

One socket per participant per room. Everything that happens in a room flows
through here as JSON messages and (when it belongs in the transcript) persists
as a RoomEvent. Board persistence stays on the existing POST save endpoint;
this layer only relays live ops between participants.
"""
import asyncio
import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings

from .models import Whiteboard, RoomEvent

# Single-process presence registry (matches InMemoryChannelLayer assumption).
PRESENCE = {}  # board_pk -> {channel_name: display_name}

LOYD_SYSTEM = (
    "You are loyd, HiHi Labs' in-room AI. You are a participant in a live "
    "collaborative whiteboard room. Below is the room's running transcript — "
    "speech, chat, board actions, and commands from everyone present. "
    "Reply conversationally and concisely (a few sentences unless asked for "
    "more). Plain text only, no markdown headers."
)


class RoomConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):
        self.board_pk = self.scope['url_route']['kwargs']['pk']
        self.group = f'room_{self.board_pk}'
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close()
            return
        self.board = await self._get_board(user)
        if self.board is None:
            await self.close()
            return
        self.user = user
        self.display = user.get_short_name() or user.username

        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

        PRESENCE.setdefault(self.board_pk, {})[self.channel_name] = self.display
        await self._broadcast_presence()
        await self._room_event('system', f'{self.display} joined the room')

    async def disconnect(self, code):
        if not hasattr(self, 'user'):
            return
        PRESENCE.get(self.board_pk, {}).pop(self.channel_name, None)
        await self.channel_layer.group_discard(self.group, self.channel_name)
        await self._broadcast_presence()
        await self._room_event('system', f'{self.display} left the room')

    # ── Inbound ──────────────────────────────────────────────────────────────

    async def receive_json(self, msg):
        t = msg.get('t')
        if t == 'board_op':
            await self._handle_board_op(msg)
        elif t == 'chat':
            await self._handle_chat(msg.get('text', '').strip())
        elif t == 'speech':
            text = msg.get('text', '').strip()
            if text:
                await self._room_event('speech', text, user=self.user)
        elif t == 'rtc':
            # WebRTC signaling relay (Phase 2): forward to one peer or all
            await self.channel_layer.group_send(self.group, {
                'type': 'room.relay', 'src': self.channel_name,
                'payload': {'t': 'rtc', 'from': self.channel_name, 'data': msg.get('data')},
                'to': msg.get('to'),
            })

    async def _handle_board_op(self, msg):
        await self.channel_layer.group_send(self.group, {
            'type': 'room.relay', 'src': self.channel_name,
            'payload': {
                't': 'board_op', 'op': msg.get('op'),
                'obj': msg.get('obj'), 'id': msg.get('id'),
            },
        })
        # Adds/removes make the transcript; modifies are too chatty.
        label = msg.get('label')
        if label and msg.get('op') in ('add', 'remove'):
            await self._room_event('board', f'{self.display} {label}', user=self.user)

    async def _handle_chat(self, text):
        if not text:
            return
        if text.startswith('/'):
            await self._handle_command(text)
            return
        await self._room_event('chat', text, user=self.user)
        if 'loyd' in text.lower():
            asyncio.ensure_future(self._loyd_reply())

    # ── Slash commands ───────────────────────────────────────────────────────

    async def _handle_command(self, text):
        parts = text.split(None, 1)
        cmd, arg = parts[0].lower(), (parts[1].strip() if len(parts) > 1 else '')

        if cmd == '/help':
            await self._room_event('system',
                'Commands: /task <title> · /note <text> · /loyd <prompt> · '
                '/summarize · /sandbox <template>|stop · /help')
        elif cmd == '/task':
            result = await self._create_task(arg or 'New task')
            await self._room_event('command', result, user=self.user,
                                   meta={'cmd': 'task'})
        elif cmd == '/note':
            if arg:
                await self._room_event('command', f'NOTE: {arg}', user=self.user,
                                       meta={'cmd': 'note'})
        elif cmd == '/loyd':
            await self._room_event('chat', text, user=self.user)
            asyncio.ensure_future(self._loyd_reply(prompt=arg or None))
        elif cmd == '/summarize':
            await self._room_event('chat', text, user=self.user)
            asyncio.ensure_future(self._loyd_reply(
                prompt='Summarize this room session so far: key decisions, '
                       'open questions, and action items.'))
        elif cmd == '/sandbox':
            await self._handle_sandbox(arg)
        else:
            await self._room_event('system', f'Unknown command {cmd} — try /help')

    async def _handle_sandbox(self, arg):
        from . import sandbox as engine
        arg = arg.strip().lower()
        if not arg or arg == 'list':
            opts = ' · '.join(f'{k} ({t["label"]})' for k, t in engine.TEMPLATES.items())
            await self._room_event('system',
                f'Usage: /sandbox <template> or /sandbox stop <id>. Templates: {opts}')
            return
        if arg.startswith('stop'):
            parts = arg.split()
            sb = await self._get_sandbox(parts[1] if len(parts) > 1 else None)
            if not sb:
                await self._room_event('system', 'No running sandbox found to stop')
                return
            await asyncio.to_thread(engine.stop, sb)
            await self._room_event('sandbox',
                f'sandbox {sb.pk} ({sb.template}) stopped',
                user=self.user, meta={'id': sb.pk, 'status': 'stopped'})
            return
        if arg not in engine.TEMPLATES:
            # not a template — maybe a real module slug
            module = await self._get_module(arg)
            if module:
                await asyncio.to_thread(self._spin_module, module)
                await self._room_event('sandbox',
                    f'{self.display} is spinning up module "{module.slug}" — '
                    'cloning/building, links land on /modules/ when ready',
                    user=self.user, meta={'module_pk': module.pk, 'slug': module.slug})
                return
        try:
            sb = await asyncio.to_thread(self._spin_sandbox, arg)
        except Exception as e:
            await self._room_event('system', f'Sandbox failed: {e}')
            return
        await self._room_event('sandbox',
            f'{self.display} spun up a {sb.template} sandbox → {engine.url_for(sb)}',
            user=self.user,
            meta={'id': sb.pk, 'template': sb.template, 'status': 'running',
                  'url': engine.url_for(sb)})

    def _spin_sandbox(self, template_key):
        from . import sandbox as engine
        return engine.spin(self.board, template_key, self.user)

    @database_sync_to_async
    def _get_module(self, slug):
        from apps.modules.models import HihiModule
        return (HihiModule.objects.filter(is_active=True, slug=slug)
                .exclude(github_url='').first())

    def _spin_module(self, module):
        from apps.modules import runner as module_runner
        module_runner.start(module, self.user)

    @database_sync_to_async
    def _get_sandbox(self, sb_id):
        from .models import Sandbox
        qs = Sandbox.objects.filter(board_id=self.board_pk, status='running')
        if sb_id and sb_id.isdigit():
            qs = qs.filter(pk=int(sb_id))
        return qs.first()

    # ── Loyd ─────────────────────────────────────────────────────────────────

    async def _loyd_reply(self, prompt=None):
        await self.channel_layer.group_send(self.group, {
            'type': 'room.relay', 'src': None,
            'payload': {'t': 'loyd_status', 'state': 'thinking'},
        })
        try:
            transcript = await self._recent_transcript()
            reply = await asyncio.to_thread(self._call_claude, transcript, prompt)
        except Exception as e:  # surface failures in-room instead of dying silently
            reply = f'(loyd hit an error: {e})'
        await self._room_event('loyd', reply)

    def _call_claude(self, transcript, prompt):
        import anthropic
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        user_msg = f'Room transcript:\n{transcript}\n\n'
        user_msg += (f'Request: {prompt}' if prompt else
                     'Respond to the latest message addressed to you.')
        resp = client.messages.create(
            model=settings.CLAUDE_CHAT_MODEL,
            max_tokens=800,
            system=LOYD_SYSTEM + f'\nRoom: "{self.board.title}"',
            messages=[{'role': 'user', 'content': user_msg}],
        )
        return resp.content[0].text

    # ── Persistence + fan-out ────────────────────────────────────────────────

    async def _room_event(self, kind, text, user=None, meta=None):
        ev = await self._save_event(kind, text, user, meta or {})
        await self.channel_layer.group_send(self.group, {
            'type': 'room.relay', 'src': None,
            'payload': {'t': 'event', 'event': ev},
        })

    async def _broadcast_presence(self):
        await self.channel_layer.group_send(self.group, {
            'type': 'room.relay', 'src': None,
            'payload': {'t': 'presence',
                        'users': sorted(set(PRESENCE.get(self.board_pk, {}).values()))},
        })

    async def room_relay(self, message):
        # Skip echo to the originator; honor targeted sends (rtc signaling)
        if message.get('src') == self.channel_name:
            return
        to = message.get('to')
        if to and to != self.channel_name:
            return
        await self.send_json(message['payload'])

    # ── DB helpers ───────────────────────────────────────────────────────────

    @database_sync_to_async
    def _get_board(self, user):
        # Rooms are collaborative: any staff member may join, not just the owner.
        if not (user.is_superuser or user.is_staff):
            return None
        return (Whiteboard.objects.filter(pk=self.board_pk)
                .select_related('project').first())

    @database_sync_to_async
    def _save_event(self, kind, text, user, meta):
        ev = RoomEvent.objects.create(board_id=self.board_pk, user=user,
                                      kind=kind, text=text, meta=meta)
        return {
            'id': ev.pk, 'kind': kind, 'text': text, 'meta': meta,
            'user': (user.get_short_name() or user.username) if user else
                    ('loyd' if kind == 'loyd' else ''),
            'ts': ev.created_at.strftime('%-I:%M %p'),
        }

    @database_sync_to_async
    def _recent_transcript(self):
        rows = (RoomEvent.objects.filter(board_id=self.board_pk)
                .select_related('user').order_by('-created_at')[:60])
        lines = []
        for ev in reversed(list(rows)):
            who = (ev.user.get_short_name() or ev.user.username) if ev.user else \
                  ('loyd' if ev.kind == 'loyd' else 'system')
            lines.append(f'[{ev.kind}] {who}: {ev.text}')
        return '\n'.join(lines) or '(transcript empty)'

    @database_sync_to_async
    def _create_task(self, title):
        project = self.board.project
        if not project:
            return f'/task "{title}" — no project linked to this board'
        from apps.projects.models import Task
        task = Task.objects.create(project=project, title=title, status='todo')
        return f'Task #{task.pk} "{title}" created in {project.name}'

"""
Seed the fleet with known services.  Safe to re-run — skips existing by name.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.servers.models import Server

SERVICES = [
    # ── VPS — Django ─────────────────────────────────────────────────────────
    dict(name='HiHi Labs CRM',      host='66.175.239.235', platform='vps',    service_type='django',
         domain='https://hihilabs.xyz',                   git_repo='https://github.com/hihilabs/hihi.labs',
         icon='fa-server', color='#7c6af7', tags='crm,vps,django',
         notes='Main CRM — projects, billing, clients, workers, fleet'),

    dict(name='Community Playlist',  host='66.175.239.235', platform='vps',   service_type='django',
         domain='https://communityplaylist.com',          git_repo='https://github.com/khildren/communityplaylist',
         icon='fa-music',  color='#2dd4bf', tags='music,events,vps,django',
         notes='Portland music community — events, food carts, flyer gen'),

    dict(name='FAC / EPK',           host='66.175.239.235', platform='vps',   service_type='django',
         domain='https://fac.hihilabs.xyz',               git_repo='https://github.com/hihilabs/epk',
         icon='fa-compact-disc', color='#e879f9', tags='fac,epk,artists,vps,django',
         notes='Federated Artist Collective — artist pages, footprint, blackbook'),

    dict(name='Seedling Society',    host='66.175.239.235', platform='vps',   service_type='django',
         domain='https://raggedgloryfarm.com',             git_repo='https://github.com/khildren/The-Seedling-Society',
         icon='fa-leaf',   color='#3ecf8e', tags='farmers-market,vps,django',
         notes='Farmers market aggregator — raggedgloryfarm.com'),

    dict(name='SS Market',           host='66.175.239.235', platform='vps',   service_type='django',
         domain='https://farm.communityplaylist.com',      git_repo='https://github.com/khildren/seedling-society-market',
         icon='fa-store',  color='#3ecf8e', tags='market,pos,vps,django'),

    dict(name='Seedling Society Shop', host='66.175.239.235', platform='vps', service_type='django',
         domain='https://seedlingsociety.com',             git_repo='https://github.com/hihilabs/up-cycle',
         icon='fa-bag-shopping', color='#f59e0b', tags='shop,printful,vps,django'),

    dict(name='Reborn Bikes',        host='66.175.239.235', platform='vps',   service_type='django',
         domain='',                                        git_repo='https://github.com/khildren/reborn-bikes',
         icon='fa-person-biking', color='#ef4444', tags='bikes,vps,django'),

    dict(name='Danklean',            host='66.175.239.235', platform='vps',   service_type='django',
         domain='https://danklean.com',                    git_repo='https://github.com/khildren/danklean',
         icon='fa-spray-can-sparkles', color='#60a5fa', tags='cleaning,vps,django'),

    dict(name='Infinity Ops',        host='66.175.239.235', platform='vps',   service_type='django',
         domain='https://infinity.milehighsfinest.shop',   git_repo='https://github.com/khildren/infinity',
         icon='fa-cannabis', color='#a3e635', tags='ops,dispensary,vps,django'),

    # ── VPS — Docker ─────────────────────────────────────────────────────────
    dict(name='edit.music',          host='66.175.239.235', platform='docker', service_type='node',
         domain='https://edit.communityplaylist.com',      git_repo='https://github.com/hihilabs/edit.music',
         icon='fa-compact-disc', color='#f472b6', tags='music,tags,docker,node',
         status_url='http://127.0.0.1:3777/api/health',
         notes='Self-hosted audio tag editor + genre orbital — Docker :3777'),

    dict(name='Genre Wiki',          host='66.175.239.235', platform='docker', service_type='django',
         domain='https://wiki.communityplaylist.com',      git_repo='https://github.com/hihilabs/communityplaylist',
         icon='fa-diagram-project', color='#818cf8', tags='genres,wiki,docker,django',
         status_url='http://127.0.0.1:3778/',
         notes='Interactive genre orbital — cp-local Django, Docker :3778'),

    # ── Unraid ───────────────────────────────────────────────────────────────
    dict(name='Unraid NAS',          host='100.94.73.80',   platform='unraid', service_type='other',
         domain='',                                        git_repo='',
         icon='fa-hard-drive', color='#f97316', tags='nas,unraid,storage,plex',
         notes='Tailscale: 100.94.73.80 — Plex, Lidarr, Radarr, Sonarr, edit.music lib'),

    dict(name='Lost Signal',         host='100.94.73.80',   platform='unraid', service_type='django',
         domain='https://lostsignal.communityplaylist.com', git_repo='https://github.com/khildren/lostsignal',
         icon='fa-signal',  color='#94a3b8', tags='unraid,django',
         notes='DB backup at /root/unraid-backups/lostsignal.sql'),

    dict(name='OmegaMEP / HiHi',    host='100.94.73.80',   platform='unraid', service_type='django',
         domain='https://omegamep.communityplaylist.com',  git_repo='',
         icon='fa-building', color='#fb923c', tags='unraid,django,omegamep',
         notes='DB backup at /root/unraid-backups/omegamep.sql'),

    # ── VPS — SSH servers ────────────────────────────────────────────────────
    dict(name='VPS (panel)',         host='66.175.239.235', platform='vps',    service_type='ssh',
         domain='',                                        git_repo='',
         icon='fa-server', color='#64748b', tags='vps,plesk,nginx',
         ssh_user='root', port=22,
         notes='Plesk — nginx → Apache → gunicorn. Tailscale: 100.123.144.69'),
]


class Command(BaseCommand):
    help = 'Seed fleet with known services'

    def handle(self, *args, **options):
        owner = User.objects.filter(is_superuser=True).first()
        if not owner:
            self.stderr.write('No superuser found.')
            return

        created = skipped = 0
        for svc in SERVICES:
            name = svc.pop('name')
            if Server.objects.filter(name=name, owner=owner).exists():
                skipped += 1
                svc['name'] = name  # restore for next run
                continue
            svc.setdefault('ssh_user', 'root')
            svc.setdefault('port', 22)
            svc.setdefault('status_url', '')
            Server.objects.create(owner=owner, name=name, **svc)
            created += 1

        self.stdout.write(self.style.SUCCESS(f'Fleet seeded: {created} created, {skipped} skipped'))

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='GameServer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='Family Server', max_length=100)),
                ('ip', models.CharField(max_length=45)),
                ('port', models.PositiveIntegerField(default=22023)),
                ('active', models.BooleanField(default=True)),
            ],
        ),
    ]

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0001_initial'),
        ('projects', '__first__'),
    ]

    operations = [
        migrations.AddField(
            model_name='hihimodule',
            name='project',
            field=models.ForeignKey(
                blank=True, null=True,
                help_text='Linked project — wiki, time log, tasks, history',
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='modules',
                to='projects.project',
            ),
        ),
    ]

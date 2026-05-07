import datetime
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Expense',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(default=datetime.date.today)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('vendor', models.CharField(max_length=200)),
                ('description', models.CharField(blank=True, max_length=300)),
                ('category', models.CharField(choices=[('software', 'Software & Subscriptions'), ('equipment', 'Equipment & Hardware'), ('home_office', 'Home Office'), ('travel', 'Travel & Transportation'), ('meals', 'Meals & Entertainment'), ('professional', 'Professional Services'), ('marketing', 'Marketing & Advertising'), ('education', 'Education & Training'), ('other', 'Other')], default='other', max_length=20)),
                ('is_deductible', models.BooleanField(default=True)),
                ('receipt', models.FileField(blank=True, null=True, upload_to='receipts/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='expenses', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-date', '-created_at']},
        ),
    ]

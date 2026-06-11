# Drops an orphaned `payment_url` column left over on billing_invoice.
# It has no corresponding model field (removed without a migration), and its
# NOT NULL constraint with no default breaks every new Invoice.objects.create().

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0002_invoice_client_fk'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE billing_invoice DROP COLUMN payment_url;",
            reverse_sql="ALTER TABLE billing_invoice ADD COLUMN payment_url varchar(200) NOT NULL DEFAULT '';",
        ),
    ]

from django.db import migrations


class Migration(migrations.Migration):
    # Merge migration to resolve parallel 0019 branches
    dependencies = [
        ('sales_proposals', '0019_alter_proposalchangelog_options_and_more'),
        ('sales_proposals', '0019_price_validity_flags'),
    ]

    operations = [
        # No-op merge
    ]


from django.db import migrations, models


def agent_to_staff(apps, schema_editor):
    UserProfile = apps.get_model('tickets', 'UserProfile')
    UserProfile.objects.filter(role='agent').update(role='staff')


def staff_to_agent(apps, schema_editor):
    UserProfile = apps.get_model('tickets', 'UserProfile')
    UserProfile.objects.filter(role='staff').update(role='agent')


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0009_documentchunk'),
    ]

    operations = [
        migrations.RunPython(agent_to_staff, staff_to_agent),
        migrations.AlterField(
            model_name='userprofile',
            name='role',
            field=models.CharField(
                choices=[('customer', 'Customer'), ('staff', 'Staff'), ('admin', 'Admin')],
                default='customer', max_length=10),
        ),
    ]

from django.db import migrations, models


def forwards(apps, schema_editor):
    UserProfile = apps.get_model("drugs", "UserProfile")
    UserProfile.objects.filter(role="patient").update(role="doctor")


class Migration(migrations.Migration):

    dependencies = [
        ("drugs", "0010_drug_specification"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="userprofile",
            name="role",
            field=models.CharField(
                choices=[
                    ("admin", "管理员"),
                    ("doctor", "医生"),
                    ("pharmacist", "药剂师"),
                ],
                default="doctor",
                max_length=20,
                verbose_name="角色",
            ),
        ),
    ]

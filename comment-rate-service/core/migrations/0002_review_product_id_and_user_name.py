from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="review",
            name="product_id",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="review",
            name="user_name",
            field=models.CharField(default="Anonymous", max_length=120),
        ),
        migrations.AlterField(
            model_name="review",
            name="book_id",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="review",
            name="customer_id",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="review",
            name="comment",
            field=models.TextField(blank=True),
        ),
    ]

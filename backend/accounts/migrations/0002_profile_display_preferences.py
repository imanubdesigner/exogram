from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='font_scale',
            field=models.FloatField(
                default=1.0,
                help_text='Multiplicador del tamaño de fuente base. Rango: 0.85–1.3.',
                verbose_name='Escala de fuente',
            ),
        ),
        migrations.AddField(
            model_name='profile',
            name='content_max_width',
            field=models.IntegerField(
                default=640,
                help_text='Ancho máximo del contenedor principal. Rango: 480–900.',
                verbose_name='Ancho máximo del contenido (px)',
            ),
        ),
    ]

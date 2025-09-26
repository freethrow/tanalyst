from django.apps import AppConfig


class ArticlesConfig(AppConfig):
    default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"
    name = "articles"

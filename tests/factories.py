from django.contrib.auth import get_user_model

import factory
from faker import Factory as FakerFactory

from pytest_factoryboy import register

faker = FakerFactory.create("fr_FR")


@register
class UserFactory(factory.DjangoModelFactory):
    email = factory.LazyFunction(faker.email)
    username = factory.LazyAttribute(lambda a: a.email)

    class Meta:
        model = get_user_model()


@register
class MagicTokenFactory(factory.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = "magicauth.MagicToken"

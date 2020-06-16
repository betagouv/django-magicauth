# Django Magicauth

Authentifiez vos utilisateurs sans mot de passe avec Django Magicauth

## Fonctionnement (FR)

Lorsqu'un service utilise Django Magicauth, les utilisateurs s'authentifient en entrant leur adresse email.
Ils reçoivent alors un email avec un lien de connexion.
S'ils cliquent sur le lien, ils sont authentifiés et redirigés sur le service.

## How it works (EN)

Django Magicauth brings password-less authentication to your project.

# Installations and testing instructions (EN)

## Quick start

1. Install MagicAuth
```sh
pip install git+https://github.com/betagouv/django-magicauth.git

```

2. Add "magicauth" to your INSTALLED_APPS in `settings.py`
```python
INSTALLED_APPS = [
    # all your apps
    "magicauth",
]

```

2. Include the magicauth URLconf in your app's `url.py`
```python
# After your previous imports
from magicauth import views as magicauth_views
from magicauth.urls import urlpatterns as magicauth_urls

urlpatterns = [
    # here are your URL patterns
]

urlpatterns.extend(magicauth_urls)
```

3. Add the following items in your project's settings.py`

```
MAGICAUTH_FROM_EMAIL = 'contact@mysite.com'
MAGICAUTH_LOGGED_IN_REDIRECT_URL_NAME = 'home'
```

4. Run `python manage.py migrate` to create the polls models.

5. Setup your (mailer)[https://docs.djangoproject.com/en/2.2/topics/email/#console-backend] in `settings.py`
In dev mode, you can use a (console mailer)[https://docs.djangoproject.com/en/2.2/topics/email/#console-backend]

6. Make sure you have the following middlewares
```
MIDDLEWARE = [
    # [...] other middleware you may have
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.sites.middleware.CurrentSiteMiddleware",
]

```
## Contribute to Magic auth

To contribute to magicauth, you can install the package in the "editable" mode

```
pip uninstall django-magicauth  # just in case...
pip install -e git+https://github.com/betagouv/django-magicauth.git#egg=django-magicauth
```

You can also install a specific branch, for instance for testing a PR. To install branch `my-branch` :

```
pip install -e git+https://github.com/betagouv/django-magicauth.git@my-branch#egg=django-magicauth
```

Django-magicauth is now a dependency for your project, and you can editable the code located here:

```
cd src/django-magicauth
```

### run tests

Create a virtual env for the project or reuse one and source it.

Install dependencies and run `tox`


```
cd src/django-magicauth
pip install -r requirements.txt
tox
```
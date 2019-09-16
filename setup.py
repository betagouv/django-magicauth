import os
from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-magicauth',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    license='',
    description='Password-less authentication: login by clicking on a magic link received by email.',
    long_description=README,
    url='',
    author='',
    author_email='',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: TODO',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)

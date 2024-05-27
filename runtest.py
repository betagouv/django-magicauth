#!/usr/bin/env python
import os
import sys

import django

import pytest

if __name__ == "__main__":
    os.environ["DJANGO_SETTINGS_MODULE"] = "tests.test_settings"
    django.setup()
    failures = pytest.main()
    sys.exit(bool(failures))

# --
# copied from file: insert_to_db.py
#
# Copyright (c) 2014-2019 Splunk, Inc.
#
# This unpublished material is proprietary to Splunk, Inc.
# All rights reserved. The methods and
# techniques described herein are considered trade secrets
# and/or confidential. Reproduction or distribution, in whole
# or in part, is forbidden except by express written permission
# of Splunk, Inc.
#
# --
import sys
import os
import json
import random
import pytz
import argparse

from collections import defaultdict
from dateutil.parser import parse as parse_datetime
from datetime import datetime, timedelta
from traceback import format_exc

django_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'www'))
sys.path.insert(0, django_path)
lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib'))
sys.path.insert(0, lib_path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'phantom_ui.settings')
import django
from django.db import transaction
from django.apps import apps as django_apps
django.setup()

import phantom_ui.ui.models as p_models
from phantom_ui.ui.shared import json_to_model, DatetimeJson
from phantom_ui.product_version import PRODUCT_VERSION

admin_user = None

def create_default_superuser(password='password'):
    u = p_models.PhUser.objects.filter(username='admin').first()

    if u:
        u.profile.delete()
        u.delete()

    u = p_models.PhUser.objects.create_superuser(username='admin', password=password,
                                                 email='root@localhost')
    u.profile = p_models.Profile()
    u.profile.set_ui_state(u.profile.get_default_ui_state())
    u.profile.save()
    u.save()
    r = p_models.Role.objects.get(name='Administrator')
    r.users.add(u)
    r.save()
    global admin_user
    admin_user = u


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--new-pass',
                        help='New password for admin user')
    args = parser.parse_args()

    create_default_superuser(password=args.new_pass)
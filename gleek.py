#!/bin/env python

# Utility to inspect (peek) at glance images
# Glance + Peek = gleek

import glanceclient.v2.client as glclient
import guestfs
import keystoneclient.v2_0.client as ksclient
from os import environ as env
import sys
from urlparse import urlparse

# Figure out endpoints
keystone = ksclient.Client(auth_url=env['OS_AUTH_URL'],
                           username=env['OS_USERNAME'],
                           password=env['OS_PASSWORD'],
                           tenant_name=env['OS_TENANT_NAME'])

glance_endpoint = keystone.service_catalog.url_for(service_type='image')
glance = glclient.Client(glance_endpoint, token=keystone.auth_token)

imagelist = glance.images.list()
for image in imagelist:
    uuid = image['id']
    location = image['direct_url']
    disk_format = image['disk_format']
    url = urlparse(location)
    disk_protocol = url.scheme
    disk = url.path.strip("/")
# Todo, how do I figure out the username? Maybe load from cfg?
    remote_username = env['RBD_CLIENT']
    g = guestfs.GuestFS(python_return_dict=True)
    g.add_drive_opts(disk, 1, disk_format,
                     protocol=disk_protocol, username=remote_username)
    g.launch()
    roots = g.inspect_os()
    for root in roots:
        print "Product name: %s" % (g.inspect_get_product_name(root))
        print "Version: %d.%d" % (g.inspect_get_major_version(root),
                                  g.inspect_get_minor_version(root))
        print "Type: %s" % (g.inspect_get_type(root))
        print "Distro: %s" % (g.inspect_get_distro(root))

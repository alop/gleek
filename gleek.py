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
    name = image['name']
    location = image['direct_url']
    format = image['disk_format']
    url = urlparse(location)
    protocol = url.scheme
    disk = url.path.lstrip("/")
    disk = disk.rstrip("/snap")
# Todo, how do I figure out the username? Maybe load from cfg?
    username = env['RBD_CLIENT']
    g = guestfs.GuestFS(python_return_dict=True)
    print "Checking %(protocol)s for %(name)s" % locals()
    try:
        g.add_drive_opts(disk, 1, format,
                         protocol=protocol, username=username)
    except RuntimeError as msg:
        print "%s (ignored)" % msg
    g.launch()
    roots = g.inspect_os()
    for root in roots:
        print "Product name for %s: %s" % (name,
                                           g.inspect_get_product_name(root))
        print "Version: %d.%d" % (g.inspect_get_major_version(root),
                                  g.inspect_get_minor_version(root))
        print "Type: %s" % (g.inspect_get_type(root))
        print "Distro: %s" % (g.inspect_get_distro(root))
    g.close()

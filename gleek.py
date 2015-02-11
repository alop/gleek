#!/bin/env python

# Utility to inspect (peek) at glance images
# Glance + Peek = gleek

import glanceclient.v2.client as glclient
import guestfs
import keystoneclient.v2_0.client as ksclient
from os import environ as env
import sqlite3
from urlparse import urlparse

# Make an images db so that we don't inspect images we already know
conn = sqlite3.connect('images.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS images(
             id text, name text, product text, version text, type text,
             distro text)''')
# Figure out endpoints
keystone = ksclient.Client(auth_url=env['OS_AUTH_URL'],
                           username=env['OS_USERNAME'],
                           password=env['OS_PASSWORD'],
                           tenant_name=env['OS_TENANT_NAME'])

glance_endpoint = keystone.service_catalog.url_for(service_type='image')
glance = glclient.Client(glance_endpoint, token=keystone.auth_token)


def inspect_image(disk, uuid, name, format, protocol, username):
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
        product = g.inspect_get_product_name(root)
        majver = g.inspect_get_major_version(root)
        minver = g.inspect_get_minor_version(root)
        version = str(majver) + "." + str(minver)
        ostype = g.inspect_get_type(root)
        distro = g.inspect_get_distro(root)
        print "Product name for %s: %s" % (name, product)
        print "Version: %s" % (version)
        print "Type: %s" % (ostype)
        print "Distro: %s" % (distro)
    g.close()
    c.execute("INSERT INTO images VALUES (?,?,?,?,?,?)",
              (uuid, name, product, version, ostype, distro))
    conn.commit()

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
    # check db if we already have this image, else get it
    exists = c.execute("SELECT id FROM images where id='%s'" % uuid).fetchone()
    if exists is None:
        inspect_image(disk, uuid, name, format, protocol, username)
    else:
        print "Image %(name)s already inspected, skipping" % locals()



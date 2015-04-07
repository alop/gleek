#!/bin/env python

# Utility to inspect (peek) at glance images
# Glance + Peek = gleek
# Copyright 2015, Abel Lopez
# All rights reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Gleek
"""

import argparse
from glanceclient import Client as glclient
import glanceclient.v2.client as gl2client
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

auth_url = ""
username = ""
password = ""
tenant_name = ""


def inspect_image(disk, uuid, name, format, protocol, rbd_client):
    """
    Clearly this is specific to rbd hosted images, however a
    future version may be more generic. 
    Inspect OS of guest using GuestFS, write results to DB and
    update glance metadata
    """
    g = guestfs.GuestFS(python_return_dict=True)
    print "Checking %(protocol)s for %(name)s" % locals()
    try:
        g.add_drive_opts(disk, 1, format,
                         protocol=protocol, username=rbd_client)
    except RuntimeError as msg:
        print "%s (ignored)" % msg
        return
    g.launch()
    roots = g.inspect_os()
    if not roots:
        product = majver = minver = version = ostype = distro = "Unknown"
    for root in roots:
        product = g.inspect_get_product_name(root)
        majver = g.inspect_get_major_version(root)
        minver = g.inspect_get_minor_version(root)
        version = str(majver) + "." + str(minver)
        ostype = g.inspect_get_type(root)
        distro = g.inspect_get_distro(root)
    g.close()
    c.execute("INSERT INTO images VALUES (?,?,?,?,?,?)",
              (uuid, name, product, version, ostype, distro))
    conn.commit()
    update_image(uuid, ostype, version, product)


def report_images():
    """
    Print out from the DB what we know about images thusfar
    Does not update glance metadata
    """
    allimages = c.execute(
        "SELECT name, product, type, distro, version from images")
    for img in allimages:
        print("Image %s is %s, which is OS type %s\n"
              "The Distribution is %s, version %s") % (img[0], img[1], img[2],
                                                       img[3], img[4])


def get_imagelist():
    """
    Connect to glance, get an image list. If the image has already been
    inspected, skip further inspection, Otherwise inspect the image
    """
    # Figure out endpoints
    keystone = ksclient.Client(auth_url=auth_url,
                               username=username,
                               password=password,
                               tenant_name=tenant_name)

    glance_endpoint = keystone.service_catalog.url_for(service_type='image')
    glance = gl2client.Client(glance_endpoint, token=keystone.auth_token)
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
        rbd_client = env['RBD_CLIENT']
        # check db if we already have this image, else get it
        exists = c.execute("SELECT id FROM images where id='%s'" % uuid)\
                  .fetchone()
        if exists is None:
            inspect_image(disk, uuid, name, format, protocol, rbd_client)
        else:
            print "Image %(name)s already inspected, skipping" % locals()


def update_image(img_id, img_os, img_ver, prod_name):
    """
    Connect to glance via v1 API, as the v2 doesn't allow setting
    arbitrary properties (yet)
    Sets os_distro, os_version, os_name in glance metadata
    """
    # Figure out endpoints
    keystone = ksclient.Client(auth_url=auth_url,
                               username=username,
                               password=password,
                               tenant_name=tenant_name)

    glance_endpoint = keystone.service_catalog.url_for(service_type='image')
    glance = glclient('1', glance_endpoint, token=keystone.auth_token)
    options = {'properties':
               {'os_distro': img_os,
                'os_version': img_ver,
                'os_name': prod_name
                }
               }
    glance.images.update(img_id, **options)


def parse_args():
    """
    Check for existence of openstack variables and rbd key
    """
    # Make sure we have all our variables sourced properly
    parser = argparse.ArgumentParser(description="Glance Peek")
    parser.add_argument('command', choices=['check', 'report'])
    try:
        parser.add_argument('--auth_url', help='Keystone endpoint',
                            default=env['OS_AUTH_URL'])
    except KeyError:
        print "OS_AUTH_URL not set, did you source openrc?"
        raise
    try:
        parser.add_argument('--os_username', help='Openstack username',
                            default=env['OS_USERNAME'])
    except KeyError:
        print "OS_USERNAME not set, did you source openrc?"
        raise
    try:
        parser.add_argument('--os_password', help='Openstack password',
                            default=env['OS_PASSWORD'])
    except KeyError:
        print "OS_PASSWORD not set, did you source openrc?"
        raise
    try:
        parser.add_argument('--os_tenant_name', help='Keystone tenant',
                            default=env['OS_TENANT_NAME'])
    except KeyError:
        print "OS_TENANT_NAME not set, did you source openrc?"
        raise
    try:
        parser.add_argument('--rbd_client_name', help='Cephx user',
                            default=env['RBD_CLIENT'])
    except KeyError:
        print "RBD_CLIENT not set"
        raise

    args = parser.parse_args()
    global auth_url
    auth_url = args.auth_url
    global username
    username = args.os_username
    global password
    password = args.os_password
    global tenant_name
    tenant_name = args.os_tenant_name

    if args.command == 'report':
        report_images()
    elif args.command == 'check':
        get_imagelist()
        report_images()


def main():
    parse_args()

if __name__ == "__main__":
    main()

#!/bin/bash

# Setup on rhel7

yum -y install ./libguestfs-1.28.1-1.18.el7.x86_64.rpm
yum install python-libguestfs python-keystoneclient python-glanceclient ceph-common
systemctl start libvirtd.service

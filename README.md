# gleek
Glance Peek

Are you using Ceph (rbd) for your glance backend?
Do you wish that you could easily inspect glance images that are stored up there?

Well, you've come to the right place.

Gleek takes a Peek inside Glance.
All you need is your admin openrc, set the name of your rbd client, and we're off to the races.

Usage:
source openrc
export RBD_CLIENT=your-glance-client

## Requirements

Gleek requires libguestfs 1.26+, which is not available via pypi
Install via package manager or Download source from http://libguestfs.org 

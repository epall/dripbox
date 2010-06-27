#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2010 Eric Allen
#
# Author: Eric Allen <eric@hackerengineer.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

# Dripbox: Keep remote copy of directory tree in sync with local tree

import os
import logging
import re

import argparse
import kqueue
import paramiko

SSH_KEY = os.path.join(os.environ['HOME'], ".ssh", "id_rsa")
LOCAL_PATH = os.getcwd()
REMOTE_REGEX = re.compile("(.*)@(.+):(.+)")
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"


def main():
    global remote_root, sftp_client
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    # parse arguments
    parser = argparse.ArgumentParser(
            description='Automatically sync local files to remote')
    parser.add_argument('-p', '--remote-port',
            type=int, default=22, help="SSH port on remote system")
    parser.add_argument('remote', nargs=1, help="user@host:path/to/remote/dir")
    args = parser.parse_args()

    remote_parts = REMOTE_REGEX.match(args.remote[0])
    username = remote_parts.group(1)
    host = remote_parts.group(2)
    remote_root = remote_parts.group(3)

    all_files = all_non_hidden_files(os.getcwd())
    sftp_client = setup_transport(username, host, args.remote_port)
    watch_files(all_files)


def setup_transport(username, host, port):
    transport = paramiko.Transport((host, port))
    key = paramiko.RSAKey.from_private_key_file(SSH_KEY)
    transport.connect(username=username, pkey=key)
    return paramiko.SFTPClient.from_transport(transport)


def update_file(full_path):
    truncated_path = full_path.replace(LOCAL_PATH, "")
    remote_path = remote_root + truncated_path
    logging.info("Uploading %s to %s" % (full_path, remote_path))
    sftp_client.put(full_path, remote_path)
    logging.info("Done")


def watch_files(file_list):
    kq = kqueue.kqueue()
    fds = []
    events = []
    for f in file_list:
        logging.debug("Opening %s, the %d file" % (f, len(fds)))
        fd = open(f, "r+")
        fds.append(fd)
        logging.debug("Got fd %s" % fd.fileno())
        ev = kqueue.EV_SET(fd.fileno(), kqueue.EVFILT_VNODE,
                kqueue.EV_ADD | kqueue.EV_ENABLE | kqueue.EV_CLEAR,
                kqueue.NOTE_DELETE, 0, fd)
        events.append(ev)

    logging.info("Waiting for event")
    while True:
        tev = kq.kevent(events, len(events), None)
        for changed in tev:
            fd = changed.udata
            update_file(fd.name)
            replacement_fd = open(fd.name, "r+")
            replacement_ev = kqueue.EV_SET(replacement_fd.fileno(),
                    kqueue.EVFILT_VNODE,
                    kqueue.EV_ADD | kqueue.EV_ENABLE | kqueue.EV_CLEAR,
                    kqueue.NOTE_DELETE, 0, replacement_fd)
            fds.append(replacement_fd)
            events.append(replacement_ev)

    for fd in fds:
        fd.close()


def all_non_hidden_files(top):
    all_files = []
    for root, dirs, files in os.walk(top):
        for d in dirs:
            if d.startswith("."):
                dirs.remove(d)
        for f in files:
            if not f.endswith(".swp"):
                all_files.append(os.path.join(root, f))
    return all_files

if __name__ == "__main__":
    main()

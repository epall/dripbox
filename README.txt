dripbox - making remote file editing easy
Author: Eric Allen <eric@hackerengineer.net>

Have you ever written code on a remote system? How did you do it? sshfs? bcvi?
vi or emacs directly on the remote system? There are many ways to do it, but I
didn't like any of the existing approaches. Enter dripbox.

Disk space is cheap, so keeping a local copy of every remote file is basically
free. If you mirror your entire remote file tree locally, then you can use 
dripbox to keep the two in sync. Every time you save a file locally, it is
automatically updated on the remote system in the background. This allows you
to use local editing tools and get lightning-fast response, but still affect
files on a remote system.

To get started, you need to have a local tree and a remote tree that are
identical. First, install dripbox:

    sudo pip install .

cd to the root of your local mirror, then start dripbox with

    drip user@host:path/to/remote/copy

Every time you modify something in the local directory tree, it will be
updated on the remote system.

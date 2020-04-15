#!/bin/bash -xe

autoreconf -if

prefix=/usr
libdir=$prefix/lib64
sysconfdir=/etc
localstatedir=/var
./configure --prefix=$prefix --libdir=$libdir --sysconfdir=$sysconfdir --localstatedir=$localstatedir

make -e rpm

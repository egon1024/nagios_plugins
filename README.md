# Nagios Plugins

This repo contains a few simple nagios callable scripts that I implemented because I couldn't
find ones that did what I was looking for elsewhere.

They are authored in Python, with an aim to keep them usable with vanilla python without extra
modules pulled in.

They are authored to serve my own purposes and while anybody is welcome to use them, I've only 
made an effort to support my own requirements.  PRs are welcome.  :)

## check_available_mem.py

This script will look at total memory in the system, and considers the memory that is either 
cached or buffered to be "available".  Run with `--help` for argument list and descriptions.

## check_dir_size.py

This script will look at the amount of space used by the total of the files within it.

I use this as one measurement as to whether a backup was successful or not.

Run with `--help` for argument list and descriptions.

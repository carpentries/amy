Deployment stuff, Bash edition

This directory contains simple scripts that help prepare a brand new machine to run amy.

## Manual prep

### Rackspace example

Rather than use the api, we will use the Cloud Control Panel for Servers to create
a new server.should I go into detail?

* make a sudo user
  * set up authorized_keys
* you might want to changes things on your box such as configure ssh not to allow password logins
  https://www.rackspace.com/blog/securing-your-ssh-server/
* switch to sudo user
* wget provision
* run provision

## provision

This script will install system and basic python dependencies and will create a user that
does not have sudo privileges. Amy will run as that user.

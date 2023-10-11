# GIST (Gist Informational Services & Technologies)

Welcome to GIST!


## Folders and Files that Belong Here
|   Folder/File     |   Purpose                                                             |
|-------------------|-----------------------------------------------------------------------|
|   `gist`          |   Django project configuration                                        |
|   `mailserver`    |   Django app that manages the databases used by postfix and dovecot   |
|   `processor`     |   Django app that is the **core functionality of gist**               |
|   `push.lua`      |   Lua push notification driver for dovecot                            |

## Folders that Need to be Moved to Infra Repo
|   Folder          |   Purpose                                                             |
|-------------------|-----------------------------------------------------------------------|
|   `postfix`       |   Copies of configuration files made for postfix                      |
|   `dovecot`       |   Copies of configuration files made for dovecot                      |
|   `nginx`         |   Copies of configuration files made for nginx                        |
|   `webmail`       |   Copies of configuration files made for roundcube/webmail            |
|   `php-fpm`       |   Copies of configuration files made for php-fpm                      |
|   `opendkim`      |   Copies of configuration files made for opendkim                     |
|   `letsencrypt`   |   Copies of configuration files made for opendkim                     |

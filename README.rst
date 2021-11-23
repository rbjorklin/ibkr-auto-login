IBKR auto-login
===============

This project assumes the following tools are installed and available on ``$PATH``:

* ``docker``
* ``docker-compose``
* ``make``
* ``curl``
* ``jq``

Quickstart
----------

* ``export IBKR_USER=<my username>``
* ``export IBKR_PASSWORD=<my password>``
* ``make up`` - This will build containers, spin them up and start the login procedure
* ``make status`` - This will print the status of your session
* ``make down`` - This tear everything down

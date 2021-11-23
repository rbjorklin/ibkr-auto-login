FROM python:3.10-bullseye

WORKDIR /auto-login

RUN pip install selenium requests
RUN mkdir -p /auto-login/img

COPY auto-login.py auto-login.py

ENTRYPOINT ["/usr/local/bin/python", "/auto-login/auto-login.py"]

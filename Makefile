PACKAGE ?= clientportal.gw.zip # Remove/add ".beta" after "clientportal" to change the install type
API_URL ?= api.ibkr.com# 1-8 are available, the default is no numbered endpoint
BASE_PATH ?= v1/api# Used to be v1/portal ?

up: down docker-build
ifndef IBKR_USER
	$(error IBKR_USER variable is not set)
endif
ifndef IBKR_PASSWORD
	$(error IBKR_PASSWORD variable is not set)
endif
	mkdir -p img logs
	docker-compose up --build --detach

docker-build:
	curl -sSLo - https://download2.interactivebrokers.com/portal/$(PACKAGE) | sha256sum > clientportal.256sum
	docker pull docker.io/library/eclipse-temurin:17
	docker build --build-arg PACKAGE=$(PACKAGE) --build-arg API_URL=$(API_URL) --tag client-portal .

down: logout
	docker-compose down --remove-orphans || true
	rm -f img/*
	rm -f logs/*

status:
	@# This should be POST according to docs?
	@# https://www.interactivebrokers.com/api/doc.html#tag/Session/paths/~1iserver~1auth~1status/post
	curl -sSk https://localhost:5000/$(BASE_PATH)/iserver/auth/status | jq
	curl -XPOST -H "Content-Length: 0" -sk https://localhost:5000/$(BASE_PATH)/iserver/auth/status | jq

validate:
	@# https://www.interactivebrokers.com/api/doc.html#tag/Session/paths/~1sso~1validate/get
	curl -sSk https://localhost:5000/$(BASE_PATH)/sso/validate | jq

tickle:
	@# This should be POST according to docs?
	@# https://www.interactivebrokers.com/api/doc.html#tag/Session/paths/~1tickle/post
	curl -sSk https://localhost:5000/$(BASE_PATH)/tickle | jq

reauth:
	@# This should be POST according to docs?
	@# https://www.interactivebrokers.com/api/doc.html#tag/Session/paths/~1iserver~1reauthenticate/post
	curl -XPOST -sSk https://localhost:5000/$(BASE_PATH)/iserver/reauthenticate | jq

logout:
	@# https://www.interactivebrokers.com/api/doc.html#tag/Session/paths/~1logout/post
	curl --connect-timeout 3 -XGET -sSk https://localhost:5000/$(BASE_PATH)/logout | jq

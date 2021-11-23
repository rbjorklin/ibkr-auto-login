FROM docker.io/library/eclipse-temurin:17

EXPOSE 5000

ARG PACKAGE=clientportal.gw.zip
ARG API_URL=api.ibkr.com

WORKDIR /client-portal
RUN apt-get update && apt-get install -y unzip curl sed
ADD clientportal.256sum clientportal.256sum
RUN curl -LO https://download2.interactivebrokers.com/portal/${PACKAGE}
RUN unzip ${PACKAGE}
RUN sed -i 's/allow:/allow:\n        - 10.*\n        - 172.*/g' root/conf.yaml
#RUN sed -i "s#proxyRemoteHost:\ .*#proxyRemoteHost: \"https://${API_URL}\"#g" root/conf.yaml
RUN sed -i "s/export\ PATH/#export PATH/g" bin/run.sh
RUN sed -i "s/export\ JAVA_HOME/#export JAVA_HOME/g" bin/run.sh
#RUN sed -i "s/config_file=\$1/config_file=\$(readlink -f \$1)/g" bin/run.sh
RUN sed -i "s/^java/java -XX:+UseZGC/g" bin/run.sh

CMD /client-portal/bin/run.sh root/conf.yaml

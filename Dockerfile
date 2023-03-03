FROM docker.io/library/eclipse-temurin:19

EXPOSE 5000

WORKDIR /client-portal
RUN apt-get update && apt-get install -y unzip curl sed

ARG PACKAGE=clientportal.gw.zip
ARG API_URL=api.ibkr.com

ADD clientportal.256sum clientportal.256sum
RUN curl -Lo /jolokia-jvm.jar https://search.maven.org/remotecontent?filepath=org/jolokia/jolokia-jvm/1.7.1/jolokia-jvm-1.7.1.jar
RUN curl -LO https://download2.interactivebrokers.com/portal/${PACKAGE}
RUN unzip ${PACKAGE}
RUN sed -i 's/allow:/allow:\n        - 10.*\n        - 172.*/g' root/conf.yaml
RUN sed -i "s#^java#java -javaagent:/jolokia-jvm.jar=host=0.0.0.0 -XX:+UseZGC -Xmx128m#g" bin/run.sh
RUN sed -i "s/export\ PATH/#export PATH/g" bin/run.sh
RUN sed -i "s/export\ JAVA_HOME/#export JAVA_HOME/g" bin/run.sh
RUN sed -i 's/config_file=$1/config_file=$(readlink -f $1)/g' bin/run.sh
RUN sed -i 's/^--conf/#--conf/g' bin/run.sh

RUN sed -i "s#proxyRemoteHost:\ .*#proxyRemoteHost: \"${API_URL}\"#g" root/conf.yaml

CMD /client-portal/bin/run.sh /client-portal/root/conf.yaml

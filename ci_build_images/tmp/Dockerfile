FROM quay.io/mariadb-foundation/bb-worker:dev_debian10

USER root

RUN apt-get -y install --no-install-recommends libeigen3-dev

WORKDIR /buildbot
USER buildbot
CMD ["dumb-init", "twistd", "--pidfile=", "-ny", "/home/buildbot/buildbot.tac"]
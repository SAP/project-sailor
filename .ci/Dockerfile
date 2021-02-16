# context must be git root:
#   docker build . -f .ci/Dockerfile -t <tag>
FROM python:3.8.6-slim

# installing git requires installing the git PPA first
RUN set -ex; \
    apt update; apt install -y --no-install-recommends gnupg ; apt-key adv --keyserver keyserver.ubuntu.com --recv-keys A1715D88E1DF1F24; \
    echo "deb http://ppa.launchpad.net/git-core/ppa/ubuntu bionic main\ndeb-src http://ppa.launchpad.net/git-core/ppa/ubuntu bionic main" >> /etc/apt/sources.list; \
    apt update; apt install -y --no-install-recommends git; \
    apt remove --purge -y gnupg; \
    apt autoremove -y --purge; apt clean -y
COPY .ci/requirements_ci.txt /tmp/requirements_ci.txt
RUN pip install --no-cache-dir -r /tmp/requirements_ci.txt
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

FROM phusion/baseimage:0.9.22
CMD ["/sbin/my_init"]

RUN apt-get -qy update && \
    apt-get -qy install --no-install-recommends virtualenv python3 python3-virtualenv && \
    mkdir /app && \
    virtualenv --python=python3 /app/env

COPY metrics.py run.sh config.ini requirements.txt /app/

RUN /app/env/bin/pip install -r /app/requirements.txt && \
    chmod +x /app/run.sh && \
    mkdir /etc/service/metrics && \
    mv /app/run.sh /etc/service/metrics/run && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

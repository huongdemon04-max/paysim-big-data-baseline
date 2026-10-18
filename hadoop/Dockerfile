# check=skip=FromPlatformFlagConstDisallowed
# The upstream image is only a source of Hadoop 3.4.1 files. Never RUN its
# AMD64 binaries: the runtime below selects the host's native architecture.
FROM --platform=linux/amd64 apache/hadoop:3.4.1@sha256:69ffa97339aff768c4e6120c3fb27aa04c121402b1c8158408a5fb5be586a30e AS distribution

FROM eclipse-temurin:11-jre-noble@sha256:f2d27d97c096185c484411da4c981892d88070d14a42b8cd25d33b92a8401a5d

ENV HADOOP_HOME=/opt/hadoop \
    HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop \
    HADOOP_LOG_DIR=/tmp/hadoop-logs \
    HADOOP_HEAPSIZE_MAX=512 \
    PATH=/opt/hadoop/bin:$PATH

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 procps \
    && rm -rf /var/lib/apt/lists/* \
    && if getent passwd 1000 >/dev/null; then \
         usermod --login hadoop --home /opt/hadoop --gid 100 "$(getent passwd 1000 | cut -d: -f1)"; \
       else \
         useradd --uid 1000 --gid 100 --home-dir /opt/hadoop --no-create-home hadoop; \
       fi \
    && mkdir -p /data/name /data/data /tmp/hadoop-logs \
    && chown -R 1000:100 /data /tmp/hadoop-logs

COPY --from=distribution --chown=1000:100 /opt/hadoop/ /opt/hadoop/
# These optional libraries are AMD64 ELF binaries. HDFS uses Java fallbacks
# on both architectures; never load foreign native code on Apple Silicon.
RUN rm -rf /opt/hadoop/lib/native
COPY entrypoint.sh /usr/local/bin/hdfs-entrypoint
COPY healthcheck.py /usr/local/bin/hdfs-healthcheck
RUN sed -i 's/\r$//' /usr/local/bin/hdfs-entrypoint \
    && chmod 755 /usr/local/bin/hdfs-entrypoint /usr/local/bin/hdfs-healthcheck

USER 1000:100
ENTRYPOINT ["/usr/local/bin/hdfs-entrypoint"]
CMD ["hdfs", "namenode"]

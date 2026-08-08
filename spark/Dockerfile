FROM apache/spark:4.0.0

USER root

ENV HOME=/opt/spark/home

RUN mkdir -p /opt/app /opt/spark/.ivy2 /opt/spark/home \
    && chown -R spark:spark /opt/app /opt/spark/.ivy2 /opt/spark/home \
    && pip3 install --no-cache-dir numpy==1.26.4 pymongo==4.10.1

COPY --chown=spark:spark package_warmup.py pipeline.py /opt/app/

USER spark

RUN /opt/spark/bin/spark-submit \
    --master 'local[1]' \
    --conf spark.jars.ivy=/opt/spark/.ivy2 \
    --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0 \
    /opt/app/package_warmup.py

CMD ["/opt/spark/bin/spark-submit", "--master", "local[2]", "/opt/app/pipeline.py"]

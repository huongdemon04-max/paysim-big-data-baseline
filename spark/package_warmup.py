from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("package-warmup").getOrCreate()
spark.range(1).count()
spark.stop()


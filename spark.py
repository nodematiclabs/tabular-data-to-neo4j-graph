from pyspark.sql import SparkSession
from pyspark.sql.functions import col, explode, udf
from pyspark.sql.types import StringType

from urllib.parse import urlparse

# Set up BigQuery details
bigquery_project_id = "tabular-to-graph"
bigquery_dataset = "helpdesk"
bigquery_materialization_dataset = "helpdesk_etl"

# Create a SparkSession
spark = SparkSession.builder \
    .appName("Helpdesk ETL PySpark Job") \
    .getOrCreate()

# Step 1: Load data from Helpdesk in BigQuery into DataFrame
pages_sql = f"""
SELECT URL as page FROM `{bigquery_project_id}.{bigquery_dataset}.url`
"""
pages_data = spark.read \
    .format("bigquery") \
    .option("project", bigquery_project_id) \
    .option("viewsEnabled", "true") \
    .option("dataset", bigquery_dataset) \
    .option("materializationProject", bigquery_project_id) \
    .option("materializationDataset", bigquery_materialization_dataset) \
    .option("query", pages_sql) \
    .load()
navigation_sql = f"""
SELECT `Source URL` as source_page, `Target URL` as target_page FROM `{bigquery_project_id}.{bigquery_dataset}.nav`
"""
navigation_data = spark.read \
    .format("bigquery") \
    .option("project", bigquery_project_id) \
    .option("viewsEnabled", "true") \
    .option("dataset", bigquery_dataset) \
    .option("materializationProject", bigquery_project_id) \
    .option("materializationDataset", bigquery_materialization_dataset) \
    .option("query", navigation_sql) \
    .load()

# Step 2a: Parse the path and the domain from the page URLs
def parsed_path(url):
    parsed_url = urlparse(url)
    return parsed_url.path
def parsed_domain(url):
    parsed_url = urlparse(url)
    return parsed_url.netloc
def parsed_page(url):
    parsed_url = urlparse(url)
    return parsed_url.netloc + parsed_url.path

parsed_path_udf = udf(parsed_path, StringType())
parsed_domain_udf = udf(parsed_domain, StringType())
parsed_page_udf = udf(parsed_page, StringType())
pages = pages_data.withColumn("path", parsed_path_udf("page"))
pages = pages.withColumn("domain", parsed_domain_udf("page"))
pages = pages.withColumn("page", parsed_page_udf("page"))
navigation = navigation_data.withColumn("source_path", parsed_path_udf("source_page"))
navigation = navigation.withColumn("source_domain", parsed_domain_udf("source_page"))
navigation = navigation.withColumn("source_page", parsed_page_udf("source_page"))
navigation = navigation.withColumn("target_path", parsed_path_udf("target_page"))
navigation = navigation.withColumn("target_domain", parsed_domain_udf("target_page"))
navigation = navigation.withColumn("target_page", parsed_page_udf("target_page"))

# Step 2c: Get counts for each page
pages = pages.groupBy("page", "path", "domain").count().withColumnRenamed("count", "view_count")
navigation = navigation.groupBy(
    "source_page",
    "source_path",
    "source_domain",
    "target_page",
    "target_path",
    "target_domain"
).count().withColumnRenamed("count", "navigation_count")

# Step 2d: Add the page counts to the navigation DataFrame with prefixes
navigation = navigation.join(pages, navigation.source_page == pages.page, "left")
navigation = navigation.withColumnRenamed("view_count", "source_view_count")
navigation = navigation.drop("page")
navigation = navigation.drop("path")
navigation = navigation.drop("domain")
navigation = navigation.join(pages, navigation.target_page == pages.page, "left")
navigation = navigation.withColumnRenamed("view_count", "target_view_count")
navigation = navigation.drop("page")
navigation = navigation.drop("path")
navigation = navigation.drop("domain")

# Step 2e: Print the schema
navigation.printSchema()

# Step 3: Load the transformed data into Neo4j
navigation.write \
    .format("org.neo4j.spark.DataSource") \
    .mode("overwrite") \
    .option("url", "neo4j://10.128.0.7") \
    .option("authentication.type", "basic") \
    .option("authentication.basic.username", "neo4j") \
    .option("authentication.basic.password", "CHANGE ME") \
    .option("relationship", "NAVIGATION") \
    .option("relationship.save.strategy", "keys") \
    .option("relationship.source.labels", ":Webpage") \
    .option("relationship.source.save.mode", "overwrite") \
    .option("relationship.source.node.keys", "source_page:page") \
    .option("relationship.source.node.properties", "source_path:path, source_domain:domain, source_view_count:view_count") \
    .option("relationship.target.labels", ":Webpage") \
    .option("relationship.target.save.mode", "overwrite") \
    .option("relationship.target.node.keys", "target_page:page") \
    .option("relationship.target.node.properties", "target_path:path, target_domain:domain, target_view_count:view_count") \
    .option("relationship.properties", "navigation_count") \
    .save()

# Stop the Spark session
spark.stop()

from __future__ import annotations

# Common technical + generic competency keywords used for offline scoring.
KEYWORDS = [
    "python", "java", "golang", "go", "javascript", ".net", "c#", "c++", "node.js",
    "typescript", "php", "ruby", "react", "angular", "vue", "flutter", "react native",
    "kotlin", "swift", "dart", "scala", "rust",
    "sql", "mysql", "postgresql", "postgres", "oracle", "mssql", "mongodb",
    "redis", "elasticsearch", "cassandra", "clickhouse", "dynamodb",
    "etl", "airflow", "spark", "pyspark", "hadoop", "kafka", "flink", "databricks",
    "bigquery", "redshift", "snowflake", "dbt", "data warehouse", "data lake", "delta",
    "pandas", "numpy", "polars", "scikit-learn", "tensorflow", "pytorch", "mlflow",
    "machine learning", "deep learning", "llm", "nlp", "langchain", "rag",
    "docker", "kubernetes", "k8s", "terraform", "ansible", "jenkins", "ci/cd",
    "git", "linux", "bash", "cloud", "aws", "gcp", "azure", "serverless",
    "microservices", "rest", "graphql", "grpc", "api", "oauth", "jwt",
    "selenium", "playwright", "pytest", "junit", "software testing", "qa",
    "excel", "sql server", "power bi", "tableau", "looker", "metabase",
    "communication", "teamwork", "leadership", "agile", "scrum",
    "problem solving", "analytical", "communication skills", "english",
    "project management", "googling",
]

BANK_TERMS = {  # simple stem -> keyword
    "nodejs": "node.js",
    "c#": ".net",
    "kubernetes": "kubernetes",
    "big data": "big data",
    "ci cd": "ci/cd",
}


def normalize(token: str) -> str:
    t = token.strip().lower()
    return BANK_TERMS.get(t, t)

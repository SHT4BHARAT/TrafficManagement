import os

class KafkaConfig:
    """
    Configuration for Redpanda/Kafka data orchestration layer.
    """
    BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    
    # Topics
    TOPIC_RAW_METADATA = "traffic.raw.metadata"
    TOPIC_OPTIMIZED_PHASES = "traffic.optimized.phases"
    TOPIC_EMERGENCY_ALERTS = "traffic.emergency.alerts"

    # Groups
    CONSUMER_GROUP_BRAIN = "daitfo-brain-group"
    CONSUMER_GROUP_UI = "daitfo-ui-group"

    @classmethod
    def get_producer_config(cls):
        return {
            'bootstrap.servers': cls.BOOTSTRAP_SERVERS,
            'client.id': 'daitfo-producer'
        }

    @classmethod
    def get_consumer_config(cls, group_id):
        return {
            'bootstrap.servers': cls.BOOTSTRAP_SERVERS,
            'group.id': group_id,
            'auto.offset.reset': 'earliest'
        }
class DBConfig:
    """
    Configuration for persistence layer (Redis, TimescaleDB, Neo4j).
    """
    # Redis (Hot Store)
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    
    # TimescaleDB (Time-series)
    TIMESCALE_HOST = os.getenv("TIMESCALE_HOST", "localhost")
    TIMESCALE_PORT = int(os.getenv("TIMESCALE_PORT", 5432))
    TIMESCALE_USER = os.getenv("TIMESCALE_USER", "postgres")
    TIMESCALE_PASS = os.getenv("TIMESCALE_PASSWORD", "postgres")
    TIMESCALE_DB = os.getenv("TIMESCALE_DB", "postgres")

    # Neo4j (Graph)
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASS = os.getenv("NEO4J_PASS", "neo4j")

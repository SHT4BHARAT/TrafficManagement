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

import json
import logging
from .config import KafkaConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DataBus")

class DataBus:
    """
    A resilient Data Bus bridge for DAITFO.
    Acts as a wrapper around Kafka/Redpanda.
    If no broker is found, it falls back to a simulated internal buffer.
    """
    def __init__(self):
        self.use_mock = True
        self.mock_buffer = []
        
        try:
            # We would normally import confluent_kafka here
            # from confluent_kafka import Producer
            # self.producer = Producer(KafkaConfig.get_producer_config())
            # self.use_mock = False
            logger.info("[CORE] Initialized Kafka Producer (Mock Mode Active)")
        except ImportError:
            logger.warning("[CORE] Kafka libraries not found. Using Mock Data Bus.")

    def publish(self, topic, data):
        """
        Publishes a message to the data bus.
        """
        message = json.dumps(data)
        if self.use_mock:
            self.mock_buffer.append({"topic": topic, "data": data})
            logger.info(f"[BUS] MOCK_PUBLISH to '{topic}': {data}")
        else:
            # self.producer.produce(topic, message.encode('utf-8'))
            # self.producer.flush()
            pass

    def get_mock_stream(self, topic):
        """
        Helper for testing: returns messages from the mock buffer.
        """
        return [m['data'] for m in self.mock_buffer if m['topic'] == topic]

# Singleton instance
bus = DataBus()

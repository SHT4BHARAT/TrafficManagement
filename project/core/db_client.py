import redis
import psycopg2
import time
from neo4j import GraphDatabase
import logging
from .config import DBConfig

logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(self):
        self.client = None
        self.connected = False
        self._connect()

    def _connect(self):
        try:
            self.client = redis.Redis(
                host=DBConfig.REDIS_HOST,
                port=DBConfig.REDIS_PORT,
                decode_responses=True,
                socket_timeout=0.5,
                socket_connect_timeout=0.5,
            )
            self.client.ping()
            self.connected = True
            logger.info("Redis connected")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self.connected = False
            self.client = None

    def _ensure(self):
        if not self.connected or self.client is None:
            return False
        try:
            self.client.ping()
            return True
        except Exception:
            logger.warning("Redis connection lost, attempting reconnect")
            self._connect()
            return self.connected

    def set_live_state(self, intersection_id: str, state: dict):
        if not self._ensure():
            return
        try:
            self.client.hset(f"intersection:{intersection_id}", mapping=state)
        except Exception as e:
            logger.error(f"Redis set_live_state failed: {e}")

    def update_live_state(self, intersection_id: str, fields: dict):
        self.set_live_state(intersection_id, fields)

    def get_live_state(self, intersection_id: str):
        if not self._ensure():
            return {}
        try:
            return self.client.hgetall(f"intersection:{intersection_id}")
        except Exception as e:
            logger.error(f"Redis get_live_state failed: {e}")
            return {}


class TimescaleClient:
    def __init__(self):
        self.conn = None
        self.connected = False
        try:
            self.conn = psycopg2.connect(
                host=DBConfig.TIMESCALE_HOST,
                port=DBConfig.TIMESCALE_PORT,
                user=DBConfig.TIMESCALE_USER,
                password=DBConfig.TIMESCALE_PASS,
                dbname=DBConfig.TIMESCALE_DB,
                connect_timeout=2,
            )
            self.connected = True
            self._init_db()
            logger.info("TimescaleDB connected")
        except Exception as e:
            logger.warning(f"TimescaleDB connection failed: {e}")
            self.connected = False
            self.conn = None

    def _init_db(self):
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS traffic_logs (
                        time TIMESTAMPTZ NOT NULL,
                        intersection_id TEXT NOT NULL,
                        avg_queue FLOAT,
                        reward FLOAT,
                        throughput INTEGER
                    );
                """)
                try:
                    cur.execute(
                        "SELECT create_hypertable('traffic_logs', 'time', if_not_exists => TRUE);"
                    )
                except Exception:
                    pass
                self.conn.commit()
        except Exception as e:
            logger.error(f"TimescaleDB init failed: {e}")

    def log_metrics(self, intersection_id: str, metrics: dict):
        if not self.connected or not self.conn:
            return
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO traffic_logs (time, intersection_id, avg_queue, reward, throughput) "
                    "VALUES (NOW(), %s, %s, %s, %s)",
                    (
                        intersection_id,
                        metrics.get("queue"),
                        metrics.get("reward"),
                        metrics.get("throughput"),
                    ),
                )
            self.conn.commit()
        except Exception as e:
            logger.error(f"TimescaleDB log_metrics failed: {e}")

    def get_recent_metrics(self, intersection_id: str, limit: int = 10) -> list:
        if not self.connected or not self.conn:
            return []
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "SELECT avg_queue, reward, throughput FROM traffic_logs "
                    "WHERE intersection_id = %s ORDER BY time DESC LIMIT %s",
                    (intersection_id, limit)
                )
                rows = cur.fetchall()
                return [{"avg_queue": r[0], "reward": r[1], "throughput": r[2]} for r in rows]
        except Exception as e:
            logger.error(f"TimescaleDB get_recent_metrics failed: {e}")
            return []


class Neo4jClient:
    def __init__(self):
        self.driver = None
        self.connected = False
        try:
            self.driver = GraphDatabase.driver(
                DBConfig.NEO4J_URI,
                auth=(DBConfig.NEO4J_USER, DBConfig.NEO4J_PASS),
                connection_timeout=2,
            )
            self.driver.verify_connectivity()
            self.connected = True
            logger.info("Neo4j connected")
        except Exception as e:
            logger.warning(f"Neo4j connection failed: {e}")
            self.connected = False
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()
            self.connected = False

    def _ensure(self):
        if not self.connected or not self.driver:
            return False
        try:
            self.driver.verify_connectivity()
            return True
        except Exception:
            logger.warning("Neo4j connection lost")
            self.connected = False
            return False

    def update_edge_weight(self, source_id: str, target_id: str, weight: float):
        if not self._ensure():
            return
        try:
            with self.driver.session() as session:
                session.run(
                    "MATCH (a:Intersection {id: $source})-[r:CONNECTS]->(b:Intersection {id: $target}) "
                    "SET r.weight = $weight",
                    source=source_id,
                    target=target_id,
                    weight=weight,
                )
        except Exception as e:
            logger.error(f"Neo4j update_edge_weight failed: {e}")

    def find_shortest_path(self, start_id: str, end_id: str):
        if not self._ensure():
            return None
        try:
            with self.driver.session() as session:
                result = session.run(
                    "MATCH (start:Intersection {id: $start}), (end:Intersection {id: $end}) "
                    "MATCH p = shortestPath((start)-[:CONNECTS*..15]->(end)) "
                    "RETURN [n in nodes(p) | n.id] AS path, length(p) AS totalCost",
                    start=start_id,
                    end=end_id,
                )
                return result.single()
        except Exception as e:
            logger.error(f"Neo4j find_shortest_path failed: {e}")
            return None

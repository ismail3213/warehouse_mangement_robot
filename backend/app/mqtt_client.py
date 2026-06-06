import os
import json
import logging
from typing import Callable, Dict, List
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MQTTClient")

MQTT_BROKER = os.getenv("MQTT_BROKER", "broker.hivemq.com")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_PREFIX = os.getenv("MQTT_TOPIC_PREFIX", "swos/ismail")

class MQTTClientManager:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.callbacks: Dict[str, List[Callable]] = {}
        
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"Connected to MQTT Broker at {MQTT_BROKER}:{MQTT_PORT} successfully.")
            # Subscribe to all required topics using prefix
            topics = [
                "truck/arrival",
                "truck/status",
                "dock/status",
                "robot/status",
                "mission/create",
                "mission/update",
                "mission/completed",
                "alert/new"
            ]
            for topic in topics:
                full_topic = f"{MQTT_PREFIX}/{topic}"
                self.client.subscribe(full_topic)
                logger.info(f"Subscribed to topic: {full_topic}")
        else:
            logger.error(f"Failed to connect to MQTT Broker, return code {rc}")
            
    def _on_message(self, client, userdata, msg):
        topic_without_prefix = msg.topic.replace(f"{MQTT_PREFIX}/", "")
        payload_str = msg.payload.decode("utf-8")
        logger.info(f"MQTT message received: {msg.topic} -> {payload_str[:200]}")
        
        try:
            payload = json.loads(payload_str)
        except Exception:
            payload = payload_str
            
        # Trigger registered callbacks for this topic
        if topic_without_prefix in self.callbacks:
            for callback in self.callbacks[topic_without_prefix]:
                try:
                    callback(payload)
                except Exception as e:
                    logger.error(f"Error executing callback for topic {msg.topic}: {e}")
                    
    def register_callback(self, topic: str, callback: Callable):
        """Register a callback for a specific topic (without prefix)"""
        if topic not in self.callbacks:
            self.callbacks[topic] = []
        self.callbacks[topic].append(callback)
        logger.info(f"Registered callback for topic: {topic}")
        
    def publish(self, topic: str, payload: dict):
        """Publish a message to a topic (adds prefix automatically)"""
        full_topic = f"{MQTT_PREFIX}/{topic}"
        payload_str = json.dumps(payload, default=str)
        logger.info(f"Publishing to MQTT: {full_topic} -> {payload_str[:200]}")
        try:
            self.client.publish(full_topic, payload_str)
        except Exception as e:
            logger.error(f"Failed to publish to MQTT topic {full_topic}: {e}")
        
    def start(self):
        logger.info(f"Starting MQTT client connection loop to {MQTT_BROKER}...")
        try:
            self.client.connect_async(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()
        except Exception as e:
            logger.warn(f"Could not initialize MQTT connection to {MQTT_BROKER} ({e}). Running in offline mode.")
        
    def stop(self):
        logger.info("Stopping MQTT client loop...")
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception as e:
            logger.error(f"Error stopping MQTT client: {e}")

# Singleton instance
mqtt_manager = MQTTClientManager()

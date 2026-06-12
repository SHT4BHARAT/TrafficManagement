import logging
import time
import json
try:
    from confluent_kafka import Consumer, KafkaError
except ImportError:
    Consumer = None
    KafkaError = None
# from pysnmp.hlapi import *  # In a real env, install pysnmp

# NTCIP Standard OIDs (Examples)
# 1.3.6.1.4.1.1206.4.2.1.1.2.1.21.1 -> Phase Status Group (ASC)
# 1.3.6.1.4.1.1206.4.2.1.1.2.1.6.1  -> Phase Green Timer

class NTCIPGateway:
    """
    Bridges AI optimized phases from Kafka to physical NTCIP controllers.
    Listens for 'traffic.optimized.phases' and sends SNMP Set requests.
    """
    def __init__(self, bootstrap_servers="localhost:9092"):
        if Consumer is None:
            self.consumer = None
            print("[GATEWAY] Kafka Consumer unavailable. NTCIP Gateway running in Simulation Fallback Mode.")
            return
            
        self.consumer = Consumer({
            'bootstrap.servers': bootstrap_servers,
            'group.id': 'ntcip-gateway-group',
            'auto.offset.reset': 'latest'
        })
        self.consumer.subscribe(['traffic.optimized.phases'])
        print("[GATEWAY] NTCIP Gateway initialized. Listening for AI commands...")

    def actuate_controller(self, controller_ip, phase_id, duration):
        """
        Simulates sending an SNMP SET command to a traffic signal controller.
        """
        print(f"[SNMP] SET {controller_ip}: Phase {phase_id} -> Force Green for {duration}s")
        # Pseudo-code for pysnmp call:
        # errorIndication, errorStatus, errorIndex, varBinds = next(
        #     setCmd(SnmpEngine(),
        #            CommunityData('public'),
        #            UdpTransportTarget((controller_ip, 161)),
        #            ContextData(),
        #            ObjectType(ObjectIdentity('1.3.6.1.4.1.1206.4.2.1.1.2.1.6.1'), Integer(duration)))
        # )
        return True

    def run(self):
        if self.consumer is None:
            print("[GATEWAY] Cannot run. Kafka Consumer is unavailable in this environment.")
            return
        try:
            while True:
                msg = self.consumer.poll(1.0)
                if msg is None: continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF: continue
                    else: print(msg.error()); break

                data = json.loads(msg.value().decode('utf-8'))
                phase = data.get("phase")
                duration = data.get("duration", 35)
                intersection_id = data.get("intersection_id", "INT_001")
                
                # Mock mapping intersection ID to a controller IP
                controller_ip = f"192.168.1.{100 + int(intersection_id.split('_')[1])}"
                self.actuate_controller(controller_ip, phase, duration)
                
        except KeyboardInterrupt:
            pass
        finally:
            self.consumer.close()

if __name__ == "__main__":
    gateway = NTCIPGateway()
    # gateway.run() # Uncomment to run in production
    
    # Manual test
    gateway.actuate_controller("192.168.1.101", "N-S Green", 45)

import os
import sys
import traci

# Add SUMO tools path
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare SUMO_HOME")

traci.start(["sumo", "-c", "osm.sumocfg"])
print("Traffic Lights Found:", traci.trafficlight.getIDList())
traci.close()
import traci
import time

traci.start(["sumo-gui", "-c", "osm.sumocfg", "--start"])

# Wait 5 seconds so GUI loads properly
time.sleep(5)

tl_id = traci.trafficlight.getIDList()[0]
print("Controlling:", tl_id)

# Run simulation for some time normally
for _ in range(300):
    traci.simulationStep()

print("Forcing phase 0...")
traci.trafficlight.setPhase(tl_id, 0)

for _ in range(300):
    traci.simulationStep()

print("Forcing phase 1...")
traci.trafficlight.setPhase(tl_id, 1)

for _ in range(300):
    traci.simulationStep()

print("Done testing.")
time.sleep(5)

traci.close()
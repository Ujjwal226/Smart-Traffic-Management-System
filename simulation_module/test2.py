import traci
import time

traci.start(["sumo-gui", "-c", "osm.sumocfg", "--start"])

tl_id = traci.trafficlight.getIDList()[0]

print("Controlling:", tl_id)

# Let vehicles spawn
for _ in range(200):
    traci.simulationStep()

print("Forcing RED for 20 seconds...")
traci.trafficlight.setRedYellowGreenState(tl_id, "rr")
for _ in range(400):  # long enough to observe
    traci.simulationStep()

print("Forcing GREEN for 20 seconds...")
traci.trafficlight.setRedYellowGreenState(tl_id, "GG")
for _ in range(400):
    traci.simulationStep()

time.sleep(5)
traci.close()
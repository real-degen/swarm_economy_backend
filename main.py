from flask import Flask, jsonify, request
import random
import threading
import time

app = Flask(__name__)

# Initialize simulation parameters
TOTAL_RESOURCES = 1_000_000
SWT_VALUE = 0.000005
GAS_COST = 0.000001  # SWT burned per agent per interaction
EXPLORER_RESOURCE_CUTOFF = 50  # Minimum resources needed for explorers to sell

# Initialize agent groups
AGENTS = {
    "traders": [{"id": i, "swt": random.randint(50, 100), "resources": random.randint(20, 50), "position": [random.randint(0, 100), random.randint(0, 100)], "alliance": None, "history": []} for i in range(1, 44)],
    "consumers": [{"id": i, "swt": random.randint(20, 50), "resources": random.randint(50, 100), "position": [random.randint(0, 100), random.randint(0, 100)], "alliance": None, "history": []} for i in range(44, 76)],
    "producers": [{"id": i, "swt": random.randint(30, 70), "resources": random.randint(0, 20), "position": [random.randint(0, 100), random.randint(0, 100)], "alliance": None, "history": []} for i in range(76, 100)],
    "governors": [{"id": i, "swt": random.randint(500, 1000), "resources": random.randint(0, 10), "position": [random.randint(0, 100), random.randint(0, 100)], "alliance": None, "history": []} for i in range(100, 112)],
    "explorers": [{"id": i, "swt": random.randint(5, 15), "resources": random.randint(0, 5), "position": [random.randint(0, 100), random.randint(0, 100)], "alliance": None, "history": []} for i in range(112, 118)],
}

# Initialize resource locations on the heatmap
RESOURCE_LOCATIONS = [{"position": [random.randint(0, 100), random.randint(0, 100)], "size": random.randint(10, 50)} for _ in range(20)]

# Alliance data structure
ALLIANCES = []

# Helper functions
def calculate_distance(pos1, pos2):
    return ((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2) ** 0.5

def find_nearest_agent(agent, agent_type):
    agents = AGENTS[agent_type]
    distances = [(other_agent, calculate_distance(agent["position"], other_agent["position"])) for other_agent in agents]
    return min(distances, key=lambda x: x[1])[0] if distances else None

def form_alliance(agent1, agent2):
    """Form an alliance between two agents."""
    if agent1["alliance"] is None and agent2["alliance"] is None:
        # Create a new alliance
        new_alliance = [agent1, agent2]
        ALLIANCES.append(new_alliance)
        agent1["alliance"] = new_alliance
        agent2["alliance"] = new_alliance
    elif agent1["alliance"] is None:
        # Add agent1 to agent2's alliance
        agent1["alliance"] = agent2["alliance"]
        agent2["alliance"].append(agent1)
    elif agent2["alliance"] is None:
        # Add agent2 to agent1's alliance
        agent2["alliance"] = agent1["alliance"]
        agent1["alliance"].append(agent2)

def break_alliance(agent1, agent2):
    """Break an alliance between two agents."""
    if agent1["alliance"] and agent2["alliance"] and agent1["alliance"] == agent2["alliance"]:
        alliance = agent1["alliance"]
        alliance.remove(agent1)
        alliance.remove(agent2)
        agent1["alliance"] = None
        agent2["alliance"] = None
        if len(alliance) < 2:
            ALLIANCES.remove(alliance)

def evaluate_alliance(agent1, agent2):
    """Determine if an alliance should form, persist, or break."""
    # Form alliance if both agents trade frequently and history shows trust
    if len(agent1["history"]) > 3 and len(agent2["history"]) > 3:
        if agent2["id"] in [entry["id"] for entry in agent1["history"] if entry["action"] == "trade"]:
            form_alliance(agent1, agent2)
    # Break alliance if cheating occurs
    if agent2["id"] in [entry["id"] for entry in agent1["history"] if entry["action"] == "cheat"]:
        break_alliance(agent1, agent2)

def simulate_interaction(agent1, agent2):
    """Simulate interactions between agents, burning SWT as gas."""
    global SWT_VALUE
    agent1["swt"] -= GAS_COST
    agent2["swt"] -= GAS_COST

    better_rate = 0.8  # Better rate for alliance members
    worse_rate = 1.2  # Worse rate for non-alliance members
    rate = 1.0

    # Determine rate based on alliance
    if agent1["alliance"] == agent2["alliance"] and agent1["alliance"] is not None:
        rate = better_rate
    elif agent1["alliance"] is not None or agent2["alliance"] is not None:
        rate = worse_rate

    # Traders
    if "traders" in [agent1["type"], agent2["type"]]:
        trade_amount = random.randint(1, 10)
        if random.choice([True, False]):
            agent1["swt"] -= trade_amount * rate
            agent2["swt"] += trade_amount * rate
            agent1["history"].append({"id": agent2["id"], "action": "trade"})
        else:
            agent1["resources"] -= trade_amount * rate
            agent2["resources"] += trade_amount * rate

    # Producers and Consumers
    if "producers" in [agent1["type"], agent2["type"]] and "consumers" in [agent1["type"], agent2["type"]]:
        trade_amount = random.randint(5, 15)
        producer = agent1 if agent1["type"] == "producers" else agent2
        consumer = agent1 if agent1["type"] == "consumers" else agent2
        producer["resources"] -= trade_amount * rate
        consumer["resources"] += trade_amount * rate
        consumer["swt"] -= trade_amount * SWT_VALUE * rate
        producer["swt"] += trade_amount * SWT_VALUE * rate
        producer["history"].append({"id": consumer["id"], "action": "trade"})

    # Evaluate alliance potential
    evaluate_alliance(agent1, agent2)

def simulate_explorer(agent):
    """Simulate explorer's behavior."""
    agent["swt"] -= GAS_COST  # Burn SWT for moving
    agent["position"] = [random.randint(0, 100), random.randint(0, 100)]  # Move randomly
    for resource in RESOURCE_LOCATIONS:
        if calculate_distance(agent["position"], resource["position"]) < 5:
            # Explorer collects resource
            agent["resources"] += resource["size"]
            RESOURCE_LOCATIONS.remove(resource)
            break

    # If explorer reaches cutoff, sell resources
    if agent["resources"] >= EXPLORER_RESOURCE_CUTOFF:
        nearest_consumer = find_nearest_agent(agent, "consumers")
        if nearest_consumer:
            nearest_consumer["resources"] += agent["resources"]
            nearest_consumer["swt"] -= agent["resources"] * SWT_VALUE
            agent["swt"] += agent["resources"] * SWT_VALUE
            agent["resources"] = 0

def simulate_turn():
    global SWT_VALUE
    
    # Ensure all agents have the 'type' key initialized before interactions
    for agent_type, agents in AGENTS.items():
        for agent in agents:
            agent["type"] = agent_type  # Initialize type for all agents

    # Simulate interactions
    for agent_type, agents in AGENTS.items():
        for agent in agents:
            if agent_type == "explorers":
                simulate_explorer(agent)
            else:
                other_agent_type = random.choice(list(AGENTS.keys()))
                other_agent = random.choice(AGENTS[other_agent_type])
                simulate_interaction(agent, other_agent)

    total_swt = sum(agent["swt"] for agents in AGENTS.values() for agent in agents)
    SWT_VALUE = max(0.0000001, TOTAL_RESOURCES / total_swt)

# Background thread for simulation
def simulation_loop():
    while True:
        simulate_turn()
        time.sleep(1)  # Adjust speed of simulation

threading.Thread(target=simulation_loop, daemon=True).start()

# API routes
# Add a default route for '/'
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Welcome to the Simulation API!"})

# Add a route for `/simulation-data`
@app.route("/simulation-data", methods=["GET"])
def simulation_data():
    return jsonify({
        "total_resources": TOTAL_RESOURCES,
        "swt_value": SWT_VALUE,
        "agents": AGENTS,
        "alliances": ALLIANCES,
        "resource_locations": RESOURCE_LOCATIONS,
    })

@app.route("/api/simulate", methods=["POST"])
def simulate_step():
    simulate_turn()
    return jsonify({"message": "Simulation step completed."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

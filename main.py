from flask import Flask, jsonify
from threading import Thread
import random
import time

app = Flask(__name__)

# Constants
SWT_VALUE = 1.0
TOTAL_RESOURCES = 1000
RESOURCE_LOCATIONS = []
AGENTS = {
    "traders": [],
    "consumers": [],
    "producers": [],
    "explorers": [],
    "governors": [],
}
ALLIANCES = []  # List of tuples containing allied group names
GAS_COST = 0.1  # Gas cost per interaction

# Agent Initialization Parameters
AGENT_COUNTS = {
    "traders": 43,
    "consumers": 32,
    "producers": 24,
    "explorers": 6,
    "governors": 12,
}

# Heatmap dimensions
HEATMAP_WIDTH = 10
HEATMAP_HEIGHT = 10

# Helper functions
def initialize_resources():
    """Initialize random resources on the heatmap."""
    global RESOURCE_LOCATIONS
    RESOURCE_LOCATIONS = [
        {
            "position": (random.randint(0, HEATMAP_WIDTH - 1), random.randint(0, HEATMAP_HEIGHT - 1)),
            "amount": random.randint(10, 50),
        }
        for _ in range(30)
    ]

def initialize_agents():
    """Create agents with starting SWT and resources."""
    for group, count in AGENT_COUNTS.items():
        for i in range(count):
            agent = {
                "id": f"{group}_{i}",
                "type": group,
                "swt": random.randint(10, 100) if group != "governors" else random.randint(500, 1000),
                "resources": random.randint(0, 50) if group != "explorers" else 0,
            }
            if group == "explorers":
                agent["position"] = (random.randint(0, HEATMAP_WIDTH - 1), random.randint(0, HEATMAP_HEIGHT - 1))
            AGENTS[group].append(agent)

def simulate_interaction(agent1, agent2):
    """Simulate interactions between two agents."""
    global SWT_VALUE

    # Burn gas for both agents
    agent1["swt"] -= GAS_COST
    agent2["swt"] -= GAS_COST

    # Interaction rules
    if "traders" in [agent1["type"], agent2["type"]]:
        # Traders exchange resources and/or SWT
        if random.choice([True, False]):
            agent1["swt"], agent2["swt"] = agent2["swt"], agent1["swt"]
        else:
            agent1["resources"], agent2["resources"] = agent2["resources"], agent1["resources"]
    elif "producers" in [agent1["type"], agent2["type"]]:
        # Producers generate resources and sell them for SWT
        if agent1["type"] == "producers":
            produced = random.randint(1, 5)
            agent1["resources"] += produced
            agent1["swt"] -= GAS_COST
        if agent2["type"] == "consumers":
            # Consumers buy resources
            price = min(agent1["resources"], agent2["swt"])
            agent1["resources"] -= price
            agent2["resources"] += price
            agent1["swt"] += price
            agent2["swt"] -= price
    elif "governors" in [agent1["type"], agent2["type"]]:
        # Governors pay more to explorers and rip off consumers
        if agent1["type"] == "governors" and agent2["type"] == "explorers":
            agent1["resources"] += agent2["resources"]
            agent2["swt"] += agent2["resources"] * 2
            agent2["resources"] = 0

def move_explorers():
    """Move explorers randomly and allow them to find resources."""
    for explorer in AGENTS["explorers"]:
        # Random movement
        new_position = (
            (explorer["position"][0] + random.choice([-1, 0, 1])) % HEATMAP_WIDTH,
            (explorer["position"][1] + random.choice([-1, 0, 1])) % HEATMAP_HEIGHT,
        )
        explorer["position"] = new_position

        # Check for resources at this position
        for resource in RESOURCE_LOCATIONS:
            if resource["position"] == new_position:
                gathered = min(resource["amount"], random.randint(1, 10))
                explorer["resources"] += gathered
                resource["amount"] -= gathered
                if resource["amount"] <= 0:
                    RESOURCE_LOCATIONS.remove(resource)
                break

def manage_alliances():
    """Handle formation and breaking of alliances."""
    global ALLIANCES

    # Form new alliances
    for group1 in AGENTS:
        for group2 in AGENTS:
            if group1 != group2 and random.random() < 0.05:  # 5% chance of alliance
                alliance = {group1, group2}
                if alliance not in ALLIANCES:
                    ALLIANCES.append(alliance)

    # Break alliances randomly
    ALLIANCES = [a for a in ALLIANCES if random.random() > 0.01]  # 1% chance of breaking

def simulate_turn():
    """Simulate a single turn of the economy."""
    move_explorers()
    manage_alliances()
    for group, agents in AGENTS.items():
        for agent in agents:
            other_agent = random.choice(agents + [a for g, a in AGENTS.items() if g != group])
            simulate_interaction(agent, other_agent)

# Flask Routes
@app.route("/simulation-data", methods=["GET"])
def simulation_data():
    """Provide simulation data."""
    serializable_agents = {
        group: [
            {
                "id": agent["id"],
                "swt": agent["swt"],
                "resources": agent["resources"],
                "type": agent["type"],
                "position": agent.get("position", None),
            }
            for agent in agents
        ]
        for group, agents in AGENTS.items()
    }
    serializable_alliances = [list(alliance) for alliance in ALLIANCES]
    serializable_resources = [
        {"position": resource["position"], "amount": resource["amount"]} for resource in RESOURCE_LOCATIONS
    ]
    return jsonify({
        "agents": serializable_agents,
        "alliances": serializable_alliances,
        "resources": serializable_resources,
        "swt_value": SWT_VALUE,
    })

# Simulation Loop
def simulation_loop():
    while True:
        simulate_turn()
        time.sleep(1)

# Initialize
initialize_resources()
initialize_agents()

# Start simulation in a separate thread
simulation_thread = Thread(target=simulation_loop, daemon=True)
simulation_thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

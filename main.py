import random
import threading
from flask import Flask, jsonify

# Flask app initialization
app = Flask(__name__)

# Global variables
total_resources = 1_000_000_000  # 1 billion resources
token_value = 0.000005  # Initial token value
agent_count = 100  # Total agents in the simulation
simulation_running = True  # Flag to control the simulation loop


# Agent class definition
class Agent:

    def __init__(self, role, resources, tokens, x, y):
        self.role = role
        self.resources = resources
        self.tokens = tokens
        self.x = x  # X-coordinate on the grid
        self.y = y  # Y-coordinate on the grid

    def move(self):
        """Move the agent randomly on a 10x10 grid."""
        self.x = max(0, min(9, self.x + random.choice([-1, 0, 1])))
        self.y = max(0, min(9, self.y + random.choice([-1, 0, 1])))


# Initialize agents
roles = ["Trader", "Explorer", "Producer", "Consumer", "Governor"]
agents = [
    Agent(
        role=random.choice(roles),
        resources=random.randint(5000, 20000),
        tokens=random.uniform(1, 10),
        x=random.randint(0, 9),
        y=random.randint(0, 9),
    ) for _ in range(agent_count)
]


# Simulate interactions
def simulate_interactions():
    global total_resources, token_value, simulation_running

    # Check if any agent has run out of both resources and tokens
    for agent in agents:
        if agent.resources == 0 and agent.tokens == 0:
            simulation_running = False
            print(
                "Simulation has ended. An agent has run out of resources and tokens."
            )
            return

    # Pick two random agents for trading
    agent1, agent2 = random.sample(agents, 2)

    # Perform resource and token exchange if possible
    if agent1.resources > 0 and agent2.tokens > 0:
        agent1.resources -= 1
        agent1.tokens += 1
        agent2.resources += 1
        agent2.tokens -= 1

    # Move all agents randomly on the grid
    for agent in agents:
        agent.move()

    # Resources naturally diminish over time
    for agent in agents:
        agent.resources = max(0, agent.resources - random.randint(1, 10))

    # Update global resources and token value
    total_resources = sum(agent.resources for agent in agents)

    # Ensure token value calculation doesn't result in division by zero
    if total_resources > 0:
        token_value = max(
            0.0000001,
            1 / total_resources)  # Prevent token value from hitting zero
    else:
        token_value = 0.0000001  # Fallback value in case total resources is zero


# Background simulation thread
def simulation_loop():
    global simulation_running
    while simulation_running:
        simulate_interactions()


# Flask API endpoints
@app.route('/api/data', methods=['GET'])
def get_data():
    """Serve the current state of the simulation."""
    global total_resources, token_value

    # Prepare data for response
    agents_data = [{
        "role": agent.role,
        "resources": agent.resources,
        "tokens": agent.tokens,
        "x": agent.x,
        "y": agent.y
    } for agent in agents]

    response = {
        "agents": agents_data,
        "total_resources": total_resources,
        "token_value": token_value,
        "agent_count": agent_count,
        "simulation_running": simulation_running
    }

    return jsonify(response)


@app.route('/api/simulate', methods=['POST'])
def simulate():
    """Run a single simulation step."""
    simulate_interactions()
    return jsonify({"message": "Simulation step completed!"})


# Start the Flask app and simulation thread
if __name__ == "__main__":
    # Start the background simulation thread
    threading.Thread(target=simulation_loop, daemon=True).start()

    # Start the Flask app
    app.run(host="0.0.0.0", port=5000)

from flask import Flask, jsonify, request
from flask_cors import CORS
import random
import os
import threading
import time

app = Flask(__name__)
CORS(app)  # Allow all origins to access this backend

# Simulation Data
total_resources = 1_000_000_000
token_value = 0.000005
agents = [{"id": i, "tokens": random.randint(100, 500), "role": random.choice(["Producer", "Consumer"]), 
           "position": {"x": random.randint(0, 500), "y": random.randint(0, 500)}}
          for i in range(100)]

# Simulate Interactions
def simulate_interactions():
    global total_resources, token_value, agents

    # Adjust resources and token value
    total_tokens = sum(agent["tokens"] for agent in agents)
    if total_tokens == 0:  # Prevent division by zero
        total_tokens = 1

    token_value = max(0.0000001, total_resources / total_tokens)

    for agent in agents:
        if agent["role"] == "Producer":
            agent["tokens"] += random.randint(10, 50)  # Producers earn tokens
        elif agent["role"] == "Consumer":
            agent["tokens"] -= random.randint(5, 30)  # Consumers spend tokens
            if agent["tokens"] < 0:
                agent["tokens"] = 0  # Prevent negative tokens

        # Update positions (random movement for heatmap)
        agent["position"]["x"] = (agent["position"]["x"] + random.randint(-10, 10)) % 500
        agent["position"]["y"] = (agent["position"]["y"] + random.randint(-10, 10)) % 500

    # End simulation if resources or tokens run out
    if any(agent["tokens"] == 0 for agent in agents):
        print("Simulation ended: An agent has run out of tokens.")
        exit()

# Background Simulation Loop
def simulation_loop():
    while True:
        simulate_interactions()
        time.sleep(2)  # Run the simulation every 2 seconds

# Start the background thread
threading.Thread(target=simulation_loop, daemon=True).start()

# Routes
@app.route("/simulation-data", methods=["GET"])
def get_simulation_data():
    global total_resources, token_value, agents
    return jsonify({
        "total_resources": total_resources,
        "token_value": token_value,
        "agents": agents
    })

@app.route("/simulate", methods=["POST"])
def simulate_step():
    simulate_interactions()
    return jsonify({"message": "Next step simulated."})

# Entry Point
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Use dynamic port for Render
    app.run(host="0.0.0.0", port=port, debug=False)

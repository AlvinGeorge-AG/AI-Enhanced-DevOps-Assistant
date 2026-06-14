# The Architecture
1. The Root Files (The Glue)
docker-compose.yml: This is the heart of your local environment. It reads the infra/ folder to start Prometheus and Nginx, builds the target_app/, and spins up your src/ Python code as the "Assistant" container.

.gitignore: You must include .env and __pycache__/ here. Never push your Groq API keys or Discord Webhook URLs to GitHub.

2. infra/ (Observability & Infrastructure)
Why it's here: This isolates all the YAML configuration files for the pre-built tools (Prometheus, AlertManager, Nginx).

Connection: Member 1 writes alertmanager.yml to specifically point its webhook URL to the Python app running from the src/api/ folder.

3. src/api/ (Core API & Context Builder)
Why it's here: This is the system's front door.

Connection: Member 2's routes.py listens for AlertManager. When an alert hits, it triggers context_builder.py, which packages the system state and hands it over to Member 3's src/brain/.

4. src/brain/ (AI & Safety)
Why it's here: This separates the unpredictable AI logic from the rest of the application.

Connection: Member 3's code takes the package from src/api/, injects it into prompts.py, gets an answer from Groq, passes it through safety_engine.py, and if it passes, hands the command down to Member 4's src/executor/.

5. src/executor/ (Action & Memory)
Why it's here: This is the only folder allowed to change the state of the infrastructure.

Connection: Member 4's action_engine.py receives the safe command and executes it using the Docker SDK. memory.py logs what happened so context_builder.py can read it during the next incident.
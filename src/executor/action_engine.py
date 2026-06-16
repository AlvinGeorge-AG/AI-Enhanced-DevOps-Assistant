# The docker-py code to scale/restart containers
import docker
import subprocess

# Connect to the host's Docker daemon
client = docker.from_env()

class ActionEngine:
    def execute(self, decision: dict):
        action = decision.get("action")
        
        if action == "scale_up" or action == "scale_down":
            self._scale(decision.get("target_replicas", 1))
        elif action == "restart_container":
            self._restart_unhealthy()
        elif action == "no_action":
            print("No action required. Continuing to monitor.")

    def _scale(self, replicas: int):
        print(f"⚡ Action Engine: Scaling infrastructure to {replicas} replicas...")
        
        # 1. Execute the scaling command on the host
        subprocess.run(
            ["docker", "compose", "up", "--scale", f"app={replicas}", "--no-recreate", "-d"],
            cwd="/project_root",
            capture_output=True, 
            text=True
        )
        
        # 2. Ask Docker for the names of the newly created containers
        containers = client.containers.list(filters={"name": "app"})
        
        upstreams = ""
        for c in containers:
            upstreams += f"        server {c.name}:5000;\n"
        
        # 3. Build the new Nginx configuration block dynamically
        nginx_config = f"""

            events {{}}
            http {{
                upstream app_backend {{
            {upstreams}    }}
                server {{
                    listen 80;
                    location / {{
                        proxy_pass http://app_backend;
                    }}
                }}
            }}
        """
        
        # 4. Overwrite the Nginx config file on the shared drive
        with open("/etc/nginx_shared/nginx.conf", "w") as f:
            f.write(nginx_config)
        
        # 5. Tell the Nginx container to reload the new config file seamlessly
        nginx_containers = client.containers.list(filters={"ancestor": "nginx:alpine"})
        if nginx_containers:
            nginx_containers[0].exec_run("nginx -s reload")
            print("✅ Action Engine: Nginx traffic routing updated with zero downtime!")

    def _restart_unhealthy(self):
        print("⚡ Action Engine: Scanning for unhealthy containers...")
        for container in client.containers.list():
            state = container.attrs.get("State", {})
            health = state.get("Health", {}).get("Status", "unknown")
            
            if health == "unhealthy":
                print(f"🔄 Restarting corrupted container: {container.name}")
                container.restart()
import docker
import subprocess

client = docker.from_env()

class ActionEngine:
    def execute(self, decision: dict):
        action = decision.get("action")
        
        if action == "scale_up":
            # Add 1 to the current count
            self._scale(direction=1)
        elif action == "scale_down":
            # Subtract 1 from the current count
            self._scale(direction=-1)
        elif action == "restart_container":
            self._restart_unhealthy()
        elif action == "no_action":
            print("No action required. Continuing to monitor.")

    def _scale(self, direction: int):
        # 1. State Awareness: Count exactly how many replicas exist right now
        current_containers = client.containers.list(filters={"label": "com.docker.compose.service=app"})
        current_count = len(current_containers)
        
        # 2. Dynamic Math: Calculate the new target
        target_replicas = current_count + direction
        
        # 3. Guardrails: Protect the system from infinite scaling
        if target_replicas < 1:
            print("⚠️ Action Engine: Already at minimum (1) replica. Cannot scale down further.")
            return
        if target_replicas > 5:
            print("⚠️ Action Engine: Max limit (5) reached. Refusing to scale up to protect system resources.")
            return

        print(f"⚡ Action Engine: Scaling from {current_count} -> {target_replicas} replicas...")
        
        # 4. Execute the dynamic scaling command
        subprocess.run(
            ["docker", "compose", "-p", "ai-enhanced-devops-assistant", "up", "--scale", f"app={target_replicas}", "--no-recreate", "-d"],
            cwd="/project_root",
            capture_output=True, 
            text=True
        )
        
        # 5. Grab the updated container list to rewrite Nginx
        new_containers = client.containers.list(filters={"label": "com.docker.compose.service=app"})
        
        upstreams = ""
        for c in new_containers:
            upstreams += f"        server {c.name}:5000;\n"
        
        # 6. Build the Nginx configuration block
        nginx_config = f"""events {{}}
        http {{
            upstream app_backend {{
        {upstreams}    }}
            server {{
                listen 80;
                location / {{
                    proxy_pass http://app_backend;
                }}
            }}
        }}"""
                
        # 7. Overwrite and smoothly reload the load balancer
        with open("/etc/nginx_shared/nginx.conf", "w") as f:
            f.write(nginx_config)
        
        nginx_containers = client.containers.list(filters={"label": "com.docker.compose.service=nginx"})
        if nginx_containers:
            nginx_containers[0].exec_run("nginx -s reload")
            print("✅ Action Engine: Nginx traffic routing updated with zero downtime!")

    def _restart_unhealthy(self):
        print("⚡ Action Engine: AI commanded a restart. Rebooting app containers...")
        # Grab all containers belonging to our app
        app_containers = client.containers.list(filters={"label": "com.docker.compose.service=app"})
        
        for container in app_containers:
            print(f"🔄 Restarting container: {container.name}")
            container.restart()
            
        print("✅ Action Engine: Restart complete.")
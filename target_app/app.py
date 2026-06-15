# A simple Python web server that exposes /metrics
from flask import Flask
from prometheus_client import make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware
import time
import math
import threading

app = Flask(__name__)

# Add prometheus wsgi middleware to route /metrics requests
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    '/metrics': make_wsgi_app()
})

def background_cpu_spike():
    """This runs in the background so Nginx doesn't timeout"""
    end_time = time.time() + 90
    while time.time() < end_time:
        math.factorial(5000)  # Much harder math
        time.sleep(0.001)     # Tiny micro-nap so Prometheus can still scrape

@app.route('/')
def hello():
    return "Target App is Running!"

@app.route('/cpu-spike')
def cpu_spike():
    # Start the heavy math on a separate background thread
    thread = threading.Thread(target=background_cpu_spike)
    thread.start()
    
    # Return immediately to avoid the 504 Timeout!
    return "CPU Spike triggered in the background! Check Prometheus."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
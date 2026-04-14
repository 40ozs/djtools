import uuid

def generate_run_id():
    return uuid.uuid4().hex[:8]
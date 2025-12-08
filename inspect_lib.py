
import pi_servo_hat
import inspect

print("Available attributes in pi_servo_hat module:")
print(dir(pi_servo_hat))

print("\nAvailable attributes in PiServoHat class:")
try:
    hat = pi_servo_hat.PiServoHat()
    print(dir(hat))
    
    # Check for helpful methods
    methods = [
        "stop", "off", "disable", "reset", "sleep", "wake", "restart"
    ]
    print("\nChecking for specific cleanup methods:")
    for m in methods:
        if hasattr(hat, m):
            print(f"Found method: {m}")
        else:
            # Check mixed case
            for attr in dir(hat):
                if m.lower() in attr.lower():
                    print(f"Found potential match for '{m}': {attr}")
                    
except Exception as e:
    print(f"Error instantiating PiServoHat: {e}")

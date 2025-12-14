'''
python3 sudodata.py \
  --signal 0 \
  --att_mean 60 --att_var 15 \
  --med_mean 45 --med_var 12 \
  --interval 0.8

'''

import random
import time
import argparse
import math

def clamp(value, low, high):
    """Clamp a value to a given range."""
    return max(low, min(high, value))

def generate_mock_output(signal_quality, att_mean, att_var, med_mean, med_var, interval):
    print("--- NEUROSKY SOCKET CLIENT (MOCK MODE) ---")
    print(f"Signal Quality fixed at: {signal_quality} (0 is Best)")
    print(f"Attention -> Normal(mean={att_mean}, var={att_var})")
    print(f"Meditation -> Normal(mean={med_mean}, var={med_var})")
    print("-------------------------------------------")

    att_std = math.sqrt(att_var)
    med_std = math.sqrt(med_var)

    while True:
        # Generate attention & meditation from normal distribution
        attention = random.gauss(att_mean, att_std)
        meditation = random.gauss(med_mean, med_std)

        # Clamp values to 0–100
        attention = clamp(int(attention), 0, 100)
        meditation = clamp(int(meditation), 0, 100)

        # Output
        print(f"Signal Quality: {signal_quality} (0 is Best)")
        print(f"--> ATTENTION: {attention}")
        print(f"--> MEDITATION: {meditation}")

        time.sleep(interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mock NeuroSky Data Generator")

    parser.add_argument("--signal", type=int, default=0,
                        help="Signal quality (default: 0)")

    parser.add_argument("--att_mean", type=float, default=50,
                        help="Mean for attention")

    parser.add_argument("--att_var", type=float, default=200,
                        help="Variance for attention")

    parser.add_argument("--med_mean", type=float, default=50,
                        help="Mean for meditation")

    parser.add_argument("--med_var", type=float, default=200,
                        help="Variance for meditation")

    parser.add_argument("--interval", type=float, default=0.3,
                        help="Seconds between outputs")

    args = parser.parse_args()

    generate_mock_output(
        args.signal,
        args.att_mean, args.att_var,
        args.med_mean, args.med_var,
        args.interval
    )

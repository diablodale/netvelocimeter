"""Example: Run a basic speed measurement using the default provider and print results.

This script demonstrates minimal usage of the netvelocimeter library.
"""

from dataclasses import asdict

from netvelocimeter import NetVelocimeter

if __name__ == "__main__":
    # Create a NetVelocimeter instance with the static provider
    nv = NetVelocimeter(provider="static")

    # ONLY FOR TESTING AND EXAMPLE PURPOSES!
    # Automatically accept all legal terms for the static provider
    nv.accept_terms(nv.legal_terms())

    # Measure the speed
    result = nv.measure()

    # Print the results
    # Iterate over the result dictionary and print each key-value pair
    print("Speed measurement result:")
    for k, v in asdict(result).items():
        print(f"{k}: {v}")

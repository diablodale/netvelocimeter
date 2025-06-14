"""Example: Select and use a specific provider with netvelocimeter, including legal terms acceptance.

This script demonstrates how to list available providers, select one, show legal terms, and run a speed test.
"""

from dataclasses import asdict

from netvelocimeter import NetVelocimeter, list_providers

if __name__ == "__main__":
    # List available providers
    print("Available providers:")
    for provider in list_providers():
        print(f"- {provider.name}: {provider.description[0] if provider.description else ''}")

    # Select a provider by name (e.g., 'ookla', 'static', etc.)
    provider_name = input("\nEnter provider name to use: ").strip()

    # Create a NetVelocimeter instance with the selected provider
    nv = NetVelocimeter(provider=provider_name)

    # Check if legal terms need to be accepted
    if nv.has_accepted_terms():
        print(f"\nLegal terms already accepted for provider '{provider_name}'.")
    else:
        # Show legal terms and prompt for acceptance
        terms = nv.legal_terms()
        print(f"\nLegal terms for provider '{provider_name}':")
        for term in terms:
            print(f"- [{term.category}] {term.url}\n  {term.text}")
        accept = input("Do you accept all required legal terms? (yes/no): ").strip().lower()
        if accept not in ("yes", "y"):
            print("You must accept the legal terms to proceed.")
            exit(1)

        # Accept the terms
        nv.accept_terms(terms)

    # Measure the speed
    result = nv.measure()

    # Print the results
    # Iterate over the result dictionary and print each key-value pair
    print(f"\nSpeed Test Result with provider '{provider_name}':")
    for k, v in asdict(result).items():
        print(f"{k}: {v}")

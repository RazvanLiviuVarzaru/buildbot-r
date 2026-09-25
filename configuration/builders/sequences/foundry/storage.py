import os

# Foundry's own storage, kept apart from the server's as the connectors' is:
# FOUNDRY_PACKAGES_DIR on the worker hosts, mounted as /packages in Foundry's
# containers, and served by nginx at <ARTIFACTS_URL>/foundry.
PACKAGES_DIR = os.environ["FOUNDRY_PACKAGES_DIR"]
ARTIFACTS_URL = f"{os.environ['ARTIFACTS_URL']}/foundry"

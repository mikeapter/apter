from _bootstrap import bootstrap
bootstrap()

from App.rules import load_rules

rules = load_rules("config/ips_rules.yaml")
print("Loaded OK. Top keys:", list(rules.keys()))
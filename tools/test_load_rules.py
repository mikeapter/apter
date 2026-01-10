from _bootstrap import bootstrap
bootstrap()

from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
ips_path = REPO_ROOT / "Config" / "ips_rules.yaml"

with ips_path.open("r", encoding="utf-8") as f:
    rules = yaml.safe_load(f)

print("Loaded keys:", list(rules.keys()))
print("Eligible asset classes:", rules.get("eligible_asset_classes"))
print("Loaded from:", str(ips_path))

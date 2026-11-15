# Compliance step: demo script (~25 seconds)

## Before presenting (once, with internet)

```bash
cd ~/Documents/hackprinceton && set -a && source .env && set +a
python3 --version   # must be 3.10+; on macOS use /opt/anaconda3/bin/python3 or a venv if this says 3.9
python3 playground/compliance_engine.py --property-id 23296 --suite A --business indoor_pickleball --live > /dev/null
python3 playground/compliance_engine.py --property-id 13890701 --business childcare --live > /dev/null
python3 playground/compliance_engine.py --property-id 966604 --business indoor_pickleball --live > /dev/null
```

Then check the replay works with no network (this is what you run on stage):

```bash
python3 playground/compliance_engine.py --property-id 23296 --suite A --business indoor_pickleball --offline | head -40
```

## What to show and say

1. **Cypresswood (the stop).** "The address says Houston, but the official boundary says unincorporated Harris County,
   so a different office permits it. And CoStar says it's apartments, so we stop before suggesting any business."
   Show: `jurisdiction.code = harris_unincorporated`, `gates = [commercial_conversion_unestablished]`.
2. **Tanner suite A, pickleball (the honest pass).** "Inside Houston city limits, so the Houston Permitting Center.
   The tour is captioned 9750, not 9700, so we flag it and don't use its measurements. The 18-foot ceiling guidance
   is marked as sport guidance, not code."
   Show: `authority`, the flagged `scan_address` record, `category_requirements.limitations`.
3. **Close.** "Every item links to an official source and stays 'needs verification'. We tell you who to call and what
   to ask; we never claim a permit."

## Lines to avoid

- Don't say "compliant" or "approved". Say "no blocker found yet, needs verification".
- Don't say the search found this building's rules. It found the city's official process pages.
- Childcare in LA: don't quote Texas numbers; the tool deliberately shows "verify CA licensing".

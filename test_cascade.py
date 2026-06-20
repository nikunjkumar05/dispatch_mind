"""Quick test of cascade module."""
import json, sys, time
sys.path.insert(0, '.')
from src.data_pipeline import run_pipeline
from src.congestion_cost import run_congestion_cost
from src.cascade import run_cascade_analysis, simulate_cascade

with open('data/external/junction_coords.json') as f:
    coords = json.load(f)

t0 = time.time()
df = run_pipeline('data/raw/violations.csv', junction_coords=coords)
df = run_congestion_cost(df, junction_coords=coords)
t1 = time.time()
print(f"\nPipeline: {t1-t0:.1f}s\n")

results = run_cascade_analysis(df, coords)
t2 = time.time()
print(f"\nCascade analysis: {t2-t1:.1f}s\n")

# Test simulation
print("Simulating cascade from Doopanahalli at 5:30 PM...")
sim = simulate_cascade(df, coords, 'BTP148 - 17th Main, Doopanahalli Bus Stop', '2024-01-15 17:30:00')
print(sim[['junction', 'step', 'delay_minutes']].to_string())

print(f"\n{'='*60}")
print(f"ALL GOOD in {t2-t0:.1f}s")
print(f"{'='*60}")

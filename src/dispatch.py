"""
ParkIntel — Stage 4: Dispatch Engine
OR-tools VRP for tow truck routing + nearest-neighbor fallback + tiered response.
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Optional


# --- Distance Matrix --------------------------------------------------------

def compute_distance_matrix(junctions: List[Tuple[float, float]]) -> np.ndarray:
    """
    Compute Euclidean distance matrix between junctions (in meters).

    Args:
        junctions: list of (lat, lon) tuples

    Returns: NxN distance matrix
    """
    n = len(junctions)
    matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            dist = np.sqrt(
                (junctions[i][0] - junctions[j][0]) ** 2 +
                (junctions[i][1] - junctions[j][1]) ** 2
            ) * 111000
            matrix[i][j] = dist
            matrix[j][i] = dist
    return matrix


# --- OR-tools VRP Solver ---------------------------------------------------

def solve_tow_truck_vrp(
    junctions: List[Tuple[float, float]],
    num_trucks: int,
    depot_index: int = 0,
    max_distance: float = 30000,
) -> Optional[List[List[Tuple[float, float]]]]:
    """
    Generate optimized tow truck routes using OR-tools VRP.

    Args:
        junctions: list of (lat, lon) to visit
        num_trucks: number of tow trucks available
        depot_index: starting point index
        max_distance: max meters per truck per shift

    Returns: list of routes (each route is a list of (lat, lon)), or None if failed
    """
    try:
        from ortools.constraint_solver import routing_enums_pb2, pywrapcp

        distance_matrix = compute_distance_matrix(junctions)
        int_matrix = (distance_matrix).astype(int).tolist()

        manager = pywrapcp.RoutingIndexManager(
            len(int_matrix), num_trucks, depot_index
        )
        routing = pywrapcp.RoutingModel(manager)

        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int_matrix[from_node][to_node]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        routing.AddDimension(
            transit_callback_index,
            0,
            int(max_distance),
            True,
            'Distance',
        )

        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.seconds = 10

        solution = routing.SolveWithParameters(search_parameters)

        if solution:
            routes = []
            for truck_id in range(num_trucks):
                route = []
                index = routing.Start(truck_id)
                while not routing.IsEnd(index):
                    node = manager.IndexToNode(index)
                    route.append(junctions[node])
                    index = solution.Value(routing.NextVar(index))
                if route:
                    routes.append(route)
            return routes

    except ImportError:
        print("  OR-tools not installed, using nearest-neighbor fallback")
    except Exception as e:
        print(f"  OR-tools failed: {e}, using nearest-neighbor fallback")

    return None


# --- Nearest-Neighbor Fallback ----------------------------------------------

def nearest_neighbor_routing(
    junctions: List[Tuple[float, float]],
    num_trucks: int,
    max_distance: float = 50000,
) -> List[List[Tuple[float, float]]]:
    """
    Greedy nearest-neighbor routing as fallback.

    Each truck visits the closest unvisited junction until max_distance reached.
    Not optimal, but always works.
    """
    unvisited = set(range(len(junctions)))
    routes = [[] for _ in range(num_trucks)]

    # Start each truck from a different point (spread coverage)
    for t in range(min(num_trucks, len(unvisited))):
        start = unvisited.pop()
        routes[t].append(junctions[start])

    current_truck = 0
    max_iterations = len(junctions) * num_trucks + 100
    iterations = 0

    while unvisited and iterations < max_iterations:
        iterations += 1

        if not routes[current_truck]:
            if unvisited:
                current = unvisited.pop()
                routes[current_truck].append(junctions[current])
            else:
                break

        # Find nearest unvisited
        best_dist = float('inf')
        best_idx = -1
        last = routes[current_truck][-1]
        for idx in unvisited:
            dist = np.sqrt(
                (last[0] - junctions[idx][0]) ** 2 +
                (last[1] - junctions[idx][1]) ** 2
            ) * 111000
            if dist < best_dist:
                best_dist = dist
                best_idx = idx

        if best_idx >= 0:
            unvisited.discard(best_idx)
            routes[current_truck].append(junctions[best_idx])
        else:
            current_truck = (current_truck + 1) % num_trucks

    return [r for r in routes if r]


# --- Tiered Response Playbook -----------------------------------------------

def generate_tiered_response(predicted_hotspots: pd.DataFrame) -> List[dict]:
    """
    Map gridlock score → enforcement action.

    Score >= 80: PRE_POSITION_TOW_TRUCK (dispatch before violation happens)
    Score >= 50: COMMUNITY_MARSHAL (alert RWA/business volunteers)
    Score < 50:  DRIVER_ALERT (SMS/Google Maps parking alert)
    """
    responses = []
    for _, row in predicted_hotspots.iterrows():
        score = row.get('gridlock_score', row.get('avg_gridlock', 0))
        junction = row.get('mapped_junction', 'Unknown')
        predicted_cost = row.get('predicted_cost', row.get('total_delay', row.get('congestion_cost', 0)))

        if score >= 80:
            action = 'PRE_POSITION_TOW_TRUCK'
            reason = f"Critical: {predicted_cost:.0f} vehicle-min predicted delay"
        elif score >= 50:
            action = 'COMMUNITY_MARSHAL'
            reason = f"High: {predicted_cost:.0f} vehicle-min predicted delay"
        else:
            action = 'DRIVER_ALERT'
            reason = f"Moderate: {predicted_cost:.0f} vehicle-min predicted delay"

        responses.append({
            'junction': junction,
            'gridlock_score': score,
            'action': action,
            'reason': reason,
            'predicted_delay': predicted_cost,
        })

    return responses


# --- Full Shift Planner -----------------------------------------------------

def plan_shift(
    df: pd.DataFrame,
    junction_coords: dict,
    num_trucks: int = 2,
    start_junction: str = None,
    max_distance: float = 30000,
) -> dict:
    """
    Plan a full tow truck shift:
    1. Identify top hotspots from historical data
    2. Generate tiered response
    3. Route trucks via VRP or fallback
    4. Return shift plan

    Args:
        df: scored violations DataFrame (or pre-aggregated hotspot_stats)
        junction_coords: dict of {name: (lat, lon)}
        num_trucks: number of tow trucks
        start_junction: starting junction name (default: highest-delay junction)
        max_distance: max meters per truck

    Returns: dict with routes, responses, summary
    """
    # Check if df is already aggregated (has 'total_delay' column)
    if 'total_delay' in df.columns:
        hotspot_stats = df.nlargest(10, 'total_delay')
    else:
        # Top 10 hotspots by total delay
        hotspot_stats = df.groupby('mapped_junction').agg(
            total_delay=('congestion_cost', 'sum'),
            violation_count=('single_violation', 'count'),
            avg_gridlock=('gridlock_score', 'mean'),
        ).reset_index().nlargest(10, 'total_delay')

    # Tiered responses
    responses = generate_tiered_response(hotspot_stats)

    # Build junction list for routing
    target_junctions = hotspot_stats['mapped_junction'].tolist()
    junction_list = []
    junction_names = []
    for jname in target_junctions:
        if jname in junction_coords:
            junction_list.append(junction_coords[jname])
            junction_names.append(jname)

    if not junction_list:
        return {
            'routes': [],
            'junction_names': [],
            'responses': responses,
            'hotspot_stats': hotspot_stats,
            'summary': {
                'routing_method': 'none (no routable junctions)',
                'num_trucks': num_trucks,
                'total_stops': 0,
                'total_distance_km': 0,
                'top_hotspot': hotspot_stats.iloc[0]['mapped_junction'] if len(hotspot_stats) > 0 else 'N/A',
                'top_hotspot_delay': hotspot_stats.iloc[0]['total_delay'] if len(hotspot_stats) > 0 else 0,
            }
        }

    # Set depot (start point)
    depot_idx = 0
    if start_junction and start_junction in junction_names:
        depot_idx = junction_names.index(start_junction)

    # Try OR-tools VRP first, fallback to nearest-neighbor
    routes = solve_tow_truck_vrp(junction_list, num_trucks, depot_idx, max_distance)
    if routes is not None:
        routing_method = 'OR-tools VRP (optimal)'
    else:
        routes = nearest_neighbor_routing(junction_list, num_trucks, max_distance)
        routing_method = 'nearest-neighbor (greedy)'

    # Summary
    total_stops = sum(len(r) for r in routes)
    total_distance = 0
    for route in routes:
        for i in range(1, len(route)):
            total_distance += np.sqrt(
                (route[i-1][0] - route[i][0]) ** 2 +
                (route[i-1][1] - route[i][1]) ** 2
            ) * 111000

    summary = {
        'routing_method': routing_method,
        'num_trucks': num_trucks,
        'total_stops': total_stops,
        'total_distance_km': round(total_distance / 1000, 1),
        'top_hotspot': hotspot_stats.iloc[0]['mapped_junction'] if len(hotspot_stats) > 0 else 'N/A',
        'top_hotspot_delay': hotspot_stats.iloc[0]['total_delay'] if len(hotspot_stats) > 0 else 0,
    }

    return {
        'routes': routes,
        'junction_names': junction_names,
        'responses': responses,
        'hotspot_stats': hotspot_stats,
        'summary': summary,
    }


# --- Run Stage 4 ------------------------------------------------------------

def run_dispatch(df: pd.DataFrame, junction_coords: dict, num_trucks: int = 2) -> dict:
    """
    Run Stage 4: Generate tow truck shift plan.

    Accepts either raw violations DataFrame (will aggregate) or pre-aggregated stats.
    """
    print("=" * 60)
    print("Stage 4: Dispatch Engine")
    print("=" * 60)

    # Pre-aggregate if needed (avoid groupby on full DataFrame in plan_shift)
    if 'total_delay' not in df.columns:
        print("  Pre-aggregating violations by junction...")
        # Use only needed columns to reduce memory
        agg_cols = ['mapped_junction', 'congestion_cost', 'single_violation', 'gridlock_score']
        available = [c for c in agg_cols if c in df.columns]
        subset = df[available]
        df = subset.groupby('mapped_junction').agg(
            total_delay=('congestion_cost', 'sum'),
            violation_count=('single_violation', 'count'),
            avg_gridlock=('gridlock_score', 'mean'),
        ).reset_index()
        print(f"  Aggregated to {len(df)} junctions")

    plan = plan_shift(df, junction_coords, num_trucks)

    print(f"\n  Routing method: {plan['summary']['routing_method']}")
    print(f"  Trucks: {plan['summary']['num_trucks']}")
    print(f"  Total stops: {plan['summary']['total_stops']}")
    print(f"  Total distance: {plan['summary']['total_distance_km']} km")
    print(f"  Top hotspot: {plan['summary']['top_hotspot']}")

    print("\n  Tiered responses:")
    for r in plan['responses'][:5]:
        print(f"    [{r['action']}] {r['junction']}: {r['reason']}")

    print("=" * 60)
    print("Stage 4 complete.")
    print("=" * 60)
    return plan


if __name__ == '__main__':
    import json
    from src.data_pipeline import run_pipeline
    from src.congestion_cost import run_congestion_cost

    with open('data/external/junction_coords.json') as f:
        coords = json.load(f)

    df = run_pipeline('data/raw/violations.csv', junction_coords=coords)
    df = run_congestion_cost(df, junction_coords=coords)
    plan = run_dispatch(df, coords, num_trucks=2)

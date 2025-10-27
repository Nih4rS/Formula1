from typing import List, Tuple

def lap_delta(ref_dist: List[float], ref_cum: List[float],
              cmp_dist: List[float], cmp_cum: List[float]) -> Tuple[List[float], List[float]]:
    x, y = [], []
    j = 0
    for i, d in enumerate(ref_dist):
        while j + 1 < len(cmp_dist) and (cmp_dist[j + 1] or 0) < (d or 0):
            j += 1
        x.append(d or 0.0)
        y.append((ref_cum[i] or 0.0) - (cmp_cum[j] or 0.0))
    return x, y

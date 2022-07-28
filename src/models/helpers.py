from typing import List

def merge_residuals(target_residual: dict, *inputs: List[dict]):
    for input in inputs:
        for (key, value) in input.items():
            if not key in target_residual:
                target_residual[key] = 0
            
            target_residual[key] += value
    
    return target_residual

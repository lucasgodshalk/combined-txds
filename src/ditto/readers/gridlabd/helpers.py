from ditto.models.base import Unicode
from typing import List, Tuple

triplex_phases = [Unicode("1"), Unicode("2")]

def parse_phases(phase_str: str, obj_name: str) -> Tuple[List[str], bool, bool]:
    phases = []

    #Lines are assumed delta by default,
    #see phases property docs: http://gridlab-d.shoutwiki.com/wiki/Power_Flow_User_Guide
    has_neutral = False
    is_triplex = False
    #is_neutral and is_delta cannot both be true, but we explicitly handle both as an error check.
    is_delta = False

    for phase_char in phase_str.strip('"').strip('|'):
        # We strip out the non-phase characters and mark them separately.
        if phase_char == "N":
            has_neutral = True
        elif phase_char == "S":
            is_triplex = True
        elif phase_char == "D":
            #Because delta is the default, the D is redundant.
            continue
        elif phase_char == "G":
            #todo: we don't handle ground phase today...
            continue
        else:
            phases.append(phase_char)
    
    if not has_neutral and not is_triplex:
        is_delta = True

    if len(phases) == 0:
        raise Exception(f"Invalid phase information (no phases provided) (obj: {obj_name}")
    elif is_triplex and (len(phases) > 1 or is_delta):
        raise Exception(f"Invalid phase information (triplex info invalid) (obj: {obj_name}")

    return (phases, is_delta, is_triplex, has_neutral)
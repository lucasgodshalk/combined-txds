from itertools import count

class Edge():
    
    _edge_ids = count(0)

    
    def __init__(self
                # , from_bus
                # , to_bus
                , edge_id = None):
        self.edge_id = edge_id if edge_id is not None else self._edge_ids.__next__()
        # self.from_bus = from_bus
        # self.to_bus = to_bus
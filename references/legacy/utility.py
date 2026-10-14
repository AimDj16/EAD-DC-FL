from collections import defaultdict
import numpy as np

def group_clients_by_model_shape(client_models):
    """
    Groups clients based on the shape of their local models' parameters.

    Args:
        client_models (dict): Mapping from client_id to model parameters.
                              Model parameters should be a list or dict of NumPy arrays.

    Returns:
        tuple:
            dict: Mapping from group_index (int) to a dict with 'shape' and 'clients' keys.
            int: Index of the group with the most complex architecture.
    """
    groups = defaultdict(list)

    for client_id, model_params in client_models.items():
        if isinstance(model_params, dict):
            shapes = tuple(param.shape for param in model_params.values())
        else:
            shapes = tuple(param.shape for param in model_params)

        groups[shapes].append(client_id)

    # Assign an index to each group and structure the return dict
    indexed_groups = {}
    max_complexity = -1
    most_complex_group_idx = None

    for idx, (shape, clients) in enumerate(groups.items()):
        complexity = sum(np.prod(dim) for dim in shape)
        if complexity > max_complexity:
            max_complexity = complexity
            most_complex_group_idx = idx
        indexed_groups[idx] = {
            "shape": shape,
            "clients": clients
        }

    return indexed_groups, most_complex_group_idx

# # Example: client models simulated by lists of numpy arrays with different shapes
# client_models = {
#     "client1": [np.random.randn(10, 20), np.random.randn(20, 5)],
#     "client2": [np.random.randn(10, 20), np.random.randn(20, 5)],
#     "client3": [np.random.randn(15, 20), np.random.randn(20, 5)],  # Different first layer shape
# }

# grouped_clients = group_clients_by_model_shape(client_models)

# for model_shape, clients in grouped_clients.items():
#     print(f"Model shape: {model_shape} -> Clients: {clients}")

def aggregate_weights(weights_list):
    """
    Aggregate a list of model weights by averaging them (FedAvg).
    weights_list: list of list of numpy arrays (weights per layer)
    Returns aggregated weights: list of numpy arrays
    """
    # Number of clients
    num_clients = len(weights_list)

    # Initialize with zeros of the same shape as first client's weights
    aggregated = []
    for layer_idx in range(len(weights_list[0])):
        layer_sum = np.zeros_like(weights_list[0][layer_idx])
        for client_weights in weights_list:
            layer_sum += client_weights[layer_idx]
        aggregated.append(layer_sum / num_clients)

    return aggregated
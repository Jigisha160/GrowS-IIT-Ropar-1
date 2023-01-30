from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.core.files import File
import pandas as pd
import requests
from geopy.geocoders import Nominatim
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import urllib.parse

# Create your views here.
# Data Structures for the routes
# Dictionary for SKUs and their weights and voulumes
# sku = {
#     'sku1': {
#         'weight': 10,
#         'volume': 10
#     },
#     'sku2': {
#         'weight': 10,
#         'volume': 10
#     }
# }
# Dictionary for the drop locations, with sku, eod, and the coordinates
# drop_locations = {
#     'drop1': {
#         'sku': 'sku1',
#         'eod': 10,
#         'coord': [28,77]
#     },
#     'drop2': {
#         'sku': 'sku2',
#         'eod': 10,
#         'coord': [28,77]
#     }
# }
# Matrix for the distances and time between the drop locations
# In this distance matrix, column 1 is drop1, column 2 is drop2, and column 3 is drop3
# distance_matrix = [
#     [0, 10, 20],
#     [10, 0, 10],
#     [20, 10, 0]
# ]
# time_matrix = [
#     [0, 10, 20],
#     [10, 0, 10],
#     [20, 10, 0]
# ]
# Dictionary for the driver routes or simply a array of arrays of drop locations

# Data needed to be passed : ‘Demands’, ‘Time windows’, ‘Vehicle capacities’, ‘Distance matrix’ and ‘Time matrix’

data_locations = {}
"""
Stores the address, latitude and longitude of different items
here key is the index of the item, i.e. node_index
Format:
{
    0: {
        'address': 'Address 1',
        'lat': latitude,
        'lon': longitude
    },
    ...
}
"""

driver_routes = []
"""
driver_routes stores all the routes for different driver
Format:
[
    [        # Route for driver 0
        [node_index, route_load, time_taken],
        [node_index, route_load, time_taken],
        [node_index, route_load, time_taken],
        [node_index, route_load, time_taken]
        ...
    ],
    [        # Route for driver 1
        [node_index, route_load, time_taken],
        [node_index, route_load, time_taken],
        [node_index, route_load, time_taken],
        [node_index, route_load, time_taken]
        ...
    ],
    ...
]

"""


all_driver_path = []
"""
Format:
[
    [        # Path for driver 0
        [lat0, long0],
        [lat1, long1],
        [lat2, long2],
        ...
    ],
    [        # Path for driver 1
        [latg0, long0],
        [latg1, long1],
        [latg2, long2],
        ...
    ],
    ...
]
"""



def index(request):
    response = {}
    response['status'] = 'OK'
    response['message'] = 'This is the home page'
    return JsonResponse(response)

def droplocations(request):
    response = {}
    response['status'] = 'OK'
    response['message'] = 'This is the drop locations page'
    return JsonResponse(response)

def get_distance(addresses):
    # Have to build the distance matrix from here
    for i in range (len(addresses)):
        addresses[i] = addresses[i].strip()
        url = 'https://nominatim.openstreetmap.org/search/' + urllib.parse.quote(addresses[i]) +'?format=json'
        response = requests.get(url).json()
        data_locations[i] = {
            'address': addresses[i],
            'lat': response[i]["lat"],
            'lon': response[i]["lon"]
        }


    # address = 'Shivaji Nagar, Bangalore, KA 560001'
    # url = 'https://nominatim.openstreetmap.org/search/' + urllib.parse.quote(address) +'?format=json'
    # response = requests.get(url).json()
    # print(response[0]["lat"])
    # print(response[0]["lon"])
        
    # print("HHH", addresses[0])
    # locator = Nominatim(user_agent="geoapiExercises")
    # print(locator)
    # location = locator.geocode("1600 Amphitheatre Parkway, Mountain View, CA")
    # print(location)



    pass
@csrf_exempt
def dispatch_addresses(request):
    if request.method == "POST":
        print("HHH", request.POST)
        print(request.FILES)
        file = request.FILES['file']
        df = pd.read_excel(file)
        # print(df)
        addresses = df['address'].tolist()
        get_distance(addresses)
        pass
    response = {}   
    response['status'] = 'OK'
    response['message'] = 'Dispatch Addresses'
    return JsonResponse(response)


def driver_route(request):
    index = request.GET.get('index')
    response = {}
    response['status'] = 'OK'
    response['message'] = 'This is the driver route page'
    response['route'] = driver_routes[index]
    return JsonResponse(response)

def admin_routes(request):
    response = {}
    response['status'] = 'OK'
    response['message'] = 'This is the admin routes page'
    # For now, hard coded the routes
    if driver_routes == []:
        cvrptw_with_dropped_locations()
    response['routes'] = driver_routes
    return JsonResponse(response)

def process_data(data):
    print(data)
    response = {}
    response['status']='OK'
    response['message']='success bitch'
    return JsonResponse(response)


def waypoint_to_coord(query):
    # Need a api that accuractely converts a waypoint to coordinates, for now using positionstack, later will replace this with a better api
    # Fetch from the api
    api = f'http://api.positionstack.com/v1/forward?access_key=318745546a93fdc9015a27db5a3fe5bc&query=${query}'
    response = requests.get(api)
    data = response.json()
    print(data)
    return data['data'][0]['latitude'], data['data'][0]['longitude']



def create_data_model():
    """Stores the data for the problem."""

    # In this we need to create time matrix using the DISTANCE API
    # Time window, vehicle capacity, demands, num_vehicles will be provided in the data
    data = {}
    data['time_matrix'] = [
                [0, 6, 9, 8, 7, 3, 6, 2, 3, 2, 6, 6, 4, 4, 5, 9, 7],
                [6, 0, 8, 3, 2, 6, 8, 4, 8, 8, 13, 7, 5, 8, 12, 10, 14],
                [9, 8, 0, 11, 10, 6, 3, 9, 5, 8, 4, 15, 14, 13, 9, 18, 9],
                [8, 3, 11, 0, 1, 7, 10, 6, 10, 10, 14, 6, 7, 9, 14, 6, 16],
                [7, 2, 10, 1, 0, 6, 9, 4, 8, 9, 13, 4, 6, 8, 12, 8, 14],
                [3, 6, 6, 7, 6, 0, 2, 3, 2, 2, 7, 9, 7, 7, 6, 12, 8],
                [6, 8, 3, 10, 9, 2, 0, 6, 2, 5, 4, 12, 10, 10, 6, 15, 5],
                [2, 4, 9, 6, 4, 3, 6, 0, 4, 4, 8, 5, 4, 3, 7, 8, 10],
                [3, 8, 5, 10, 8, 2, 2, 4, 0, 3, 4, 9, 8, 7, 3, 13, 6],
                [2, 8, 8, 10, 9, 2, 5, 4, 3, 0, 4, 6, 5, 4, 3, 9, 5],
                [6, 13, 4, 14, 13, 7, 4, 8, 4, 4, 0, 10, 9, 8, 4, 13, 4],
                [6, 7, 15, 6, 4, 9, 12, 5, 9, 6, 10, 0, 1, 3, 7, 3, 10],
                [4, 5, 14, 7, 6, 7, 10, 4, 8, 5, 9, 1, 0, 2, 6, 4, 8],
                [4, 8, 13, 9, 8, 7, 10, 3, 7, 4, 8, 3, 2, 0, 4, 5, 6],
                [5, 12, 9, 14, 12, 6, 6, 7, 3, 3, 4, 7, 6, 4, 0, 9, 2],
                [9, 10, 18, 6, 8, 12, 15, 8, 13, 9, 13, 3, 4, 5, 9, 0, 9],
                [7, 14, 9, 16, 14, 8, 5, 10, 6, 5, 4, 10, 8, 6, 2, 9, 0],
            ]
    # According to our problem, the first parameter will be zero only
    data['time_windows'] = [
                (0, 60),  # depot
                (0, 30),  # 1
                (0, 40),  # 2
                (0, 50),  # 3
                (0, 30),  # 4
                (0, 40),  # 5
                (0, 60),  # 6
                (0, 50),  # 7
                (0, 50),  # 8
                (0, 30),  # 9
                (0, 40),  # 10
                (0, 15),  # 11
                (0, 5),  # 12
                (0, 10),  # 13
                (0, 8),  # 14
                (0, 15),  # 15
                (0, 15),  # 16
              ]
    data['demands'] = [0, 1, 1, 2, 4, 2, 4, 8, 3, 1, 2, 1, 2, 4, 4, 5, 5]
    data['vehicle_capacities'] = [15, 15]
    data['num_vehicles'] = 2
    data['depot'] = 0
    return data

def get_solution(data, manager, routing, assignment, time_callback):
    All_Routes = []

    """Prints assignment on console."""
    print(f'Objective: {assignment.ObjectiveValue()}')
    # Display dropped nodes.
    dropped_nodes = 'Dropped nodes:'
    for node in range(routing.Size()):
        if routing.IsStart(node) or routing.IsEnd(node):
            continue
        if assignment.Value(routing.NextVar(node)) == node:
            dropped_nodes += ' {}'.format(manager.IndexToNode(node))
    print(dropped_nodes)
    # Display routes
    total_distance = 0
    total_load = 0
    for vehicle_id in range(data['num_vehicles']):
        index = routing.Start(vehicle_id)
        route_load = 0

        routes = []

        while not routing.IsEnd(index):

            node_index = manager.IndexToNode(index)
            time_taken = time_callback(index, index+1)
            route_load += data['demands'][node_index]
            
            route = []
            route.append(node_index)
            route.append(route_load)
            route.append(time_taken)
            routes.append(route)

            index = assignment.Value(routing.NextVar(index))
        
        All_Routes.append(routes)
    
    # Just for checking purposes
    driver_routes = All_Routes
    return All_Routes

def cvrptw_with_dropped_locations():
    # This function will be used to calculate the routes with dropped locations
    
    # Instantiate the data problem
    data = create_data_model()

    # Create the routing index manager
    manager = pywrapcp.RoutingIndexManager(len(data['time_matrix']),data['num_vehicles'], data['depot'])
    
    # Create Routing Model
    routing = pywrapcp.RoutingModel(manager)

    # Create and register a transit callback.
    def time_callback(from_index, to_index):
        """Returns the travel time between the two nodes."""
        # Convert from routing variable Index to time matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data['time_matrix'][from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(time_callback)

    # Define cost of each arc.
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Add Capacity constraint.
    def demand_callback(from_index):
        """Returns the demand of the node."""
        # Convert from routing variable Index to demands NodeIndex.
        from_node = manager.IndexToNode(from_index)
        return data['demands'][from_node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,  # null capacity slack
        data['vehicle_capacities'],  # vehicle maximum capacities
        True,  # start cumul to zero
        'Capacity')
    
    # Allow to drop nodes.
    penalty = 1000
    for node in range(1, len(data['time_matrix'])):
        routing.AddDisjunction([manager.NodeToIndex(node)], penalty)

    # Add Time Windows constraint.
    time = 'Time'
    # routing.AddDimension(transit_callback_index,
    #     30,  # allow waiting time
    #     30,  # maximum time per vehicle
    #     False,  # Don't force start cumul to zero.
    #     time)
    time_dimension = routing.GetDimensionOrDie(time)
    
    # Add time window constraints for each location except depot.
    for location_idx, time_window in enumerate(data['time_windows']):
        if location_idx == 0:
            continue
        index = manager.NodeToIndex(location_idx)
        time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])

    # Setting first solution heuristic.
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    search_parameters.time_limit.FromSeconds(10)

    # Solve the problem.
    assignment = routing.SolveWithParameters(search_parameters)

    # Print solution on console.
    solution = None
    if assignment:
        solution = get_solution(data, manager, routing, assignment, time_callback)
    

@csrf_exempt
def get_waypoint_to_coord(request):
    # read the query from the request
    query = request.GET.get('query')
    print("query",query)
    lat, lon = waypoint_to_coord(query)
    print(lat,lon)
    response = {}
    response['status'] = 'OK'
    response['message'] = 'Waypoint to coordinates'
    response['lat'] = lat
    response['lon'] = lon
    return JsonResponse(response)



def find_kth_delivery_item(k):
    # This function finds information of the kth delivery item being delivered
    # It returns a list of the following format:
    # [driver_index, node_index, route_load, total_time]
    # Here total_time is the time taken to reach the kth delivery item from the depot


    # Creating a list of tuple of all items being delivered and then finally we will sort it to find kth item
    # The tuple will be of the format (driver_index, node_index, route_load, total_time)
    all_items = []
    driver_index = 0
    for routes in driver_routes:
        time = 0
        for route in routes:
            node_index = route[0]
            route_load = route[1]
            time_taken = route[2]
            time += time_taken
            all_items.append((driver_index, node_index, route_load, time))
        driver_index += 1
    
    # Sorting the list of tuples
    all_items.sort(key = lambda x: x[3])

    # Returning the kth item
    try:
        return all_items[k]
    except IndexError:
        print("IndexError in find_kth_delivery_item function: k is greater than the number of items being delivered")




def update_driver_routes(k):
    # This function updates the driver_routes list after the kth delivery item has been delivered
    # All the items before the kth item will be removed from the list
    # kth item will also be removed from the driver_routes list

    # Creating a list of tuple of all items being delivered and then finally we will sort it to find kth item
    # The tuple will be of the format (total_time, driver_index, node_index, route_load, time_taken)
    all_items = []
    driver_index = 0
    for routes in driver_routes:
        time = 0
        for route in routes:
            node_index = route[0]
            route_load = route[1]
            time_taken = route[2]
            time += time_taken
            all_items.append((time, driver_index, node_index, route_load, time_taken))
        driver_index += 1
    
    # Sorting the list of tuples
    all_items.sort(key = lambda x: x[0])

    # Creating updated driver_routes list
    updated_driver_routes = [[] for _ in range(len(driver_routes))]
    for i in range(k, len(all_items)):
        driver_index = all_items[i][1]
        updated_driver_routes[driver_index].append(all_items[i][2:])
    
    # Updating the driver_routes list
    global driver_routes
    driver_routes = updated_driver_routes

def date_driver_ropaths():
    # Generates the driver_paths list from the driver_routes list
    # Uses data_locations to get the coordinates of the nodes
    global driver_paths
    driver_paths = [[] for _ in range(len(driver_routes))]
    for i in range(len(driver_routes)):
        for route in driver_routes[i]:
            node_index = route[0]
            driver_paths[i].append([
                data_locations[node_index]["lat"],
                data_locations[node_index]["lon"]
            ])
    

import quantimize.converter as cv
import quantimize.data_access as da
import numpy as np
import scipy.interpolate as interpolate
import matplotlib.pyplot as plt


def straight_line_trajectory(flight_nr, dt):
    """
    :param flight_nr: Flight number
    :param dt: The time step in minutes
    :return: Trajectory in the format of a list of tuples (time, longitude, latitude) embeded in a dict with flightnumber
    """
    info = da.get_flight_info(flight_nr)
    slope = (info['end_latitudinal'] - info['start_latitudinal']) * 111 / \
            ((info['end_longitudinal'] - info['start_longitudinal']) * 85)
    flight_level = info['start_flightlevel']
    speed = cv.ms_to_kms(cv.kts_to_ms(da.get_flight_level_data(flight_level)['CRUISE']['TAS']))
    total_distance = cv.coordinates_to_distance(info['start_longitudinal'], info['start_latitudinal'],
                                                info['end_longitudinal'], info['end_latitudinal'])
    current_coord = info['start_longitudinal'], info['start_latitudinal'], flight_level, info['start_time']
    trajectory = [current_coord]
    current_distance = 0
    while current_distance < total_distance:
        current_distance += speed*dt
        time = cv.update_time(current_coord[3], dt)
        longitude = current_coord[0] + speed * dt * np.cos(np.arctan(slope)) / 85
        latitude = current_coord[1] + speed * dt * np.sin(np.arctan(slope)) / 111
        current_coord = longitude, latitude, flight_level, time
        trajectory.append(current_coord)
    trajectory[-1] = (info['end_longitudinal'], info['end_latitudinal'], flight_level, current_coord[3])
    return trajectory


def straight_line_solution(flight_nr, dt):
    """
    :param flight_nr: Flight number
    :param dt: The time step in minutes
    :return: Trajectory in the format of a list of tuples (time, longitude, latitude) embeded in a dict with flightnumber
    """
    trajectory = straight_line_trajectory(flight_nr, dt)
    return {"flight_nr": flight_nr, "trajectory": trajectory}


def fit_spline(x, y, k=3):
    t, c, k = interpolate.splrep(x, y, s=0, k=k)
    spline = interpolate.BSpline(t, c, k, extrapolate=False)
    return spline


def plot_b_spline(spline, x, y, N=100):
    xx = np.linspace(np.min(x), np.max(x), N)
    plt.plot(x, y, 'bo', label='Control points')
    plt.plot(xx, spline(xx), 'r', label='BSpline')
    plt.grid()
    plt.legend(loc='best')
    plt.show()


def spline_trajectory(flight_nr, spline_xy, spline_z, dx):
    info = da.get_flight_info(flight_nr)
    sign = 1 if info['start_longitudinal'] <= info['end_longitudinal'] else -1
    current_coord = info['start_longitudinal'], info['start_latitudinal'], info['start_flightlevel'], info['start_time']
    trajectory = [current_coord]
    current_distance = 0
    slope = (info['end_latitudinal'] - info['start_latitudinal']) * 111 / \
            ((info['end_longitudinal'] - info['start_longitudinal']) * 85)
    dd = np.sqrt(dx**2 + (slope*dx)**2)*85
    while True:  # This should always be true if the plane is on the trajectory
        longitude = current_coord[0] + sign * dx
        latitude = spline_xy(longitude)
        current_distance += dd
        flight_level = spline_z(current_distance)
        if sign == 1 and longitude > info['end_longitudinal']:
            break
        elif sign == -1 and longitude < info['end_longitudinal']:
            break
        else:
            if flight_level > current_coord[2]:
                dt1 = int((flight_level - current_coord[2]) /
                          cv.ftm_to_fls(da.get_flight_level_data((flight_level+current_coord[2])/2)['CLIMB']['ROC']))
            else:
                dt1 = int((current_coord[2] - flight_level) /
                          cv.ftm_to_fls(da.get_flight_level_data((flight_level+current_coord[2])/2)['DESCENT']['ROD']))
            speed = cv.ms_to_kms(cv.kts_to_ms(da.get_flight_level_data((flight_level +
                                                                        current_coord[2])/2)['CRUISE']['TAS']))
            dt = int(cv.coordinates_to_distance(current_coord[0], current_coord[1], longitude, latitude) / speed)
            intermediate_coord = (longitude * (1 - dt1 / dt) + current_coord[0] * dt1 / dt,
                                  latitude * (1 - dt1 / dt) + current_coord[1] * dt1 / dt,
                                  flight_level,
                                  cv.update_time(current_coord[3], dt1))
            current_coord = longitude, latitude, flight_level, cv.update_time(current_coord[3], dt)
            trajectory.append(intermediate_coord)
            trajectory.append(current_coord)
    speed = cv.ms_to_kms(cv.kts_to_ms(da.get_flight_level_data(current_coord[2])['CRUISE']['TAS']))
    dt = int(cv.coordinates_to_distance(current_coord[0], current_coord[1],
                                        info['end_longitudinal'], info['end_latitudinal']) / speed)
    time = cv.update_time(current_coord[3], dt)
    trajectory.append((info['end_longitudinal'], info['end_latitudinal'], current_coord[2], time))
    return trajectory


def genetic_algorithm():
    pass


def fitness_function(flight_nr, ctrl_pts):
    """
    Takes in a list of 11 parameters for control points, first 3 for x, next 3 for y, last 5 for z.
    obtain a trajectory and then compute cost
    :return:
    """
    info = da.get_flight_info(flight_nr)
    x = [info['start_longitudinal']] + ctrl_pts[:3] + [info['end_longitudinal']]
    y = [info['start_latitudinal']] + ctrl_pts[3:6] + [info['end_latitudinal']]
    z = [info['start_flightlevel']] + ctrl_pts[6:]
    total_distance = cv.coordinates_to_distance(info['start_longitudinal'], info['start_latitudinal'],
                                                info['end_longitudinal'], info['end_latitudinal'])
    spline_xy = fit_spline(x, y)
    spline_z = fit_spline(np.linspace(0, total_distance, 6), z)
    trajectory = {"flight_nr": flight_nr, "trajectory": spline_trajectory(flight_nr, spline_xy, spline_z, 0.3)}
    cost = compute_cost(trajectory)
    return cost


def compute_cost(trajectory):
    """Returns the cost for a given list of trajectories in 10**-12

    Args:
        trajectory (list of trajectory dicts): List of trajectory dicts
        dt (int): Timestep in seconds

    Returns:
        float, int: cost in 10**-12 K and flight number
    """
    cost = 0
    t = cv.datetime_to_seconds(trajectory["trajectory"][0][3])
    start_level = trajectory["trajectory"][0][2]
    for coordinate in trajectory["trajectory"][1:]:
        print(cost)
        print(coordinate)
        if coordinate[2] == start_level:
            cost += (da.get_merged_atmo_data(*coordinate)) * da.get_flight_level_data(coordinate[2])['CRUISE']['fuel']\
                    * (cv.datetime_to_seconds(coordinate[3])-t) / 60
        elif coordinate[2] < start_level:
            cost += (da.get_merged_atmo_data(*coordinate)) * da.get_flight_level_data(coordinate[2])['DESCENT']['fuel']\
                    * (cv.datetime_to_seconds(coordinate[3])-t) / 60
            start_level = coordinate[2]
        else:
            cost += (da.get_merged_atmo_data(*coordinate)) * da.get_flight_level_data(coordinate[2])['CLIMB']['fuel']\
                    * (cv.datetime_to_seconds(coordinate[3])-t) / 60
            start_level = coordinate[2]
        t = cv.datetime_to_seconds(coordinate[3])
    return cost, trajectory["flight_nr"]

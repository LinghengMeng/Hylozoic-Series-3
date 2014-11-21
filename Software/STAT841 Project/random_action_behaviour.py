import math
import random
from RegionsManager import Expert
from SimSystem import SimpleFunction as Robot
import matplotlib.pyplot as plt
import pickle
import numpy as np
from copy import copy

import Visualization as Viz


if __name__ == "__main__":

    # number of time step
    sim_duration = 5000

    # use saved expert
    is_using_saved_expert = 0

    # initial actions
    Mi = ((0,),)

    # instantiate a Robot
    robot = Robot()

    # instantiate an Expert
    if is_using_saved_expert:
        with open('expert_backup.pkl', 'rb') as input:
            expert = pickle.load(input)
        with open('action_history_backup.pkl', 'rb') as input:
            action_history = pickle.load(input)
        with open('state_history_backup.pkl', 'rb') as input:
            state_history = pickle.load(input)

        with open('mean_error_history_backup.pkl', 'rb') as input:
            mean_error_history = pickle.load(input)

    else:
        expert = Expert()
        action_history = []
        state_history = []
        mean_error_history = []

        # initial training action
        Mi = robot.get_possible_action(num_sample=100)


    # initial conditions
    t = 0
    S = (0,)
    M = Mi[0]
    L = float("-inf")
    exploring_rate = 0.1

    while t < sim_duration:
        t += 1

        print("\nTest case t =", t, " -- ", S, M)

        # have the expert make prediction
        S1_predicted = expert.predict(S, M)
        print("Predicted S1: ", S1_predicted)


        # do action
        action_history.append(M)
        state_history.append(S)
        robot.actuate(M)

        # read sensor
        S1 = robot.report()

        # add exemplar to expert
        expert.append(S + M, S1, S1_predicted)

        # split is being done within append
        # expert.split()  # won't actually split if the condition is not met


        # random action or the best action
        print("Exploring Rate: ", exploring_rate)
        is_exploring = (random.random() < exploring_rate)

        #START ---- the Oudeyer way ----- START

        # generate a list of possible action given the state
        M_candidates = robot.get_possible_action(state=S1, num_sample=50)

        if is_exploring:
            M1 = random.choice(M_candidates)

        else:
            M1 = 0
            highest_L = float("-inf")
            for M_candidate in M_candidates:
                L = expert.evaluate_action(S1, M_candidate)
                if L > highest_L:
                    M1 = M_candidate
                    highest_L = L

            print("Expected Reward", highest_L)
            L = highest_L

        print("Next Action", M1)

        # record the mean errors of each region
        mean_errors = []
        region_ids = []
        expert.save_mean_errors(mean_errors)
        mean_error_history.append(copy(mean_errors))

        # set to current state

        S = S1
        if t < len(Mi):
            M = Mi[t]
        else:
            M = M1


        if t % 1000 == 0 or t >= sim_duration:
            with open('expert_backup.pkl', 'wb') as output:
                pickle.dump(expert, output, pickle.HIGHEST_PROTOCOL)

            with open('action_history_backup.pkl', 'wb') as output:
                pickle.dump(action_history, output, pickle.HIGHEST_PROTOCOL)

            with open('state_history_backup.pkl', 'wb') as output:
                pickle.dump(state_history, output, pickle.HIGHEST_PROTOCOL)

            with open('mean_error_history_backup.pkl', 'wb') as output:
                pickle.dump(mean_error_history, output, pickle.HIGHEST_PROTOCOL)


    expert.print()

    # find out what are the ids that existed
    region_ids = sorted(list(zip(*mean_error_history[-1]))[0])

    Viz.plot_expert_tree(expert, region_ids)
    Viz.plot_evolution(state_history, title='State vs Time', y_label='S(t)', fig_num=1, subplot_num=261)
    Viz.plot_evolution(action_history, title='Action vs Time', y_label='M(t)', fig_num=1, subplot_num=262)
    Viz.plot_model(expert, region_ids, x_idx=1, y_idx=0, fig_num=1, subplot_num=263)
    Viz.plot_model(expert, region_ids, x_idx=0, y_idx=0, fig_num=1, subplot_num=269)
    Viz.plot_regional_mean_errors(mean_error_history, region_ids, fig_num=1, subplot_num=234)
    Viz.plot_model_3D(expert, region_ids, x_idx=(0, 1), y_idx=0, fig_num=1, subplot_num=122)

    plt.ioff()
    plt.show()

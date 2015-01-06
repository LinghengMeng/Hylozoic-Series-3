import math
import random

import matplotlib.pyplot as plt
import pickle
import numpy as np
from copy import copy
import Visualization as Viz
import os
import threading
from time import sleep

from RegionsManager import Expert
# from SimSystem import DiagonalPlane as Robot
import InteractiveCmd
from InteractiveCmd import command_object


def weighted_choice_sub(weights, min_percent=0.05):
    min_weight = min(weights)
    weights = [x-min_weight for x in weights]
    adj_val = min_percent*max(weights)
    weights = [x+adj_val for x in weights]

    rnd = random.random() * sum(weights)
    for i, w in enumerate(weights):
        rnd -= w
        if rnd < 0:
            return i

    return random.randint(0, len(weights)-1)

class CBLA_Behaviours(InteractiveCmd.InteractiveCmd):


    class Node():

        def __init__(self, interactive_cmd,  teensy_name):

            self.interactive_cmd = interactive_cmd
            self.M0 = (0, )
            self.S = (0, )
            self.teensy_name = teensy_name



        def actuate(self, M):

            # move tentacle 0 up
            cmd_obj = command_object(self.teensy_name, 'protocell')
            cmd_obj.add_param_change('protocell_0_led_level', int(M[0]))
            self.M0 = M

            with self.interactive_cmd.lock:
                self.interactive_cmd.enter_command(cmd_obj)

            self.interactive_cmd.write_barrier.wait()


        def report(self):

            self.interactive_cmd.read_barrier.wait()

            with self.interactive_cmd.lock:
                sample = self.interactive_cmd.get_input_states((self.teensy_name,), ('all',))[self.teensy_name][0]

            s = sample['protocell_0_als_state']
            self.S = (s,)
            return self.S

        def get_possible_action(self, state=None, num_sample=1000):

            x_dim = 1

            X = np.zeros((num_sample, x_dim))

            for i in range(num_sample):
                X[i, x_dim-1] = max(min(self.M0[x_dim-1]-int(num_sample/2) + i, 255), 0)

            M_candidates = tuple(map(tuple, X))

            return M_candidates


    class CBLA_Engine(threading.Thread):

        def __init__(self, robot):

            # ~~ configuration ~~
            self.is_using_saved_expert = 0

            # number of time step
            self.sim_duration = 2000

            # use adaptive learning rate
            self.adapt_exploring_rate = False

            # exploring rate
            self.exploring_rate = 0.05



            # ~~ instantiation ~~

            self.robot = robot

            # instantiate an Expert
            if self.is_using_saved_expert:
                with open('expert_backup.pkl', 'rb') as input:
                    self.expert = pickle.load(input)
                with open('action_history_backup.pkl', 'rb') as input:
                    self.action_history = pickle.load(input)
                with open('state_history_backup.pkl', 'rb') as input:
                    self.state_history = pickle.load(input)
                with open('mean_error_history_backup.pkl', 'rb') as input:
                    self.mean_error_history = pickle.load(input)

            else:

                self.expert = Expert()
                self.action_history = []
                self.state_history = []
                self.mean_error_history = []


            # ~~ initiating threads ~~
            threading.Thread.__init__(self)
            self.daemon = False
            self.start()

        def run(self):

            # initial training action
            Mi = self.robot.get_possible_action(num_sample=10)

            # initial conditions
            t = 0
            S = (0,)
            M = Mi[0]
            L = float("-inf")


            while t < self.sim_duration:

                t += 1
                term_print_str = self.robot.teensy_name
                term_print_str += ''.join(map(str, ("\nTest case t = ", t, " -- ", S, M, '\n')))


                # have the expert make prediction
                S1_predicted = self.expert.predict(S, M)

                term_print_str += ''.join(map(str, ("Predicted S1: ", S1_predicted, '\n')))


                # do action
                self.action_history.append(M)
                self.state_history.append(S)
                self.robot.actuate(M)
                sleep(0.1)

                # read sensor
                S1 = self.robot.report()
                term_print_str += ''.join(map(str, ("Actual S1: ", S1, '\n')))


                # add exemplar to expert
                self.expert.append(S + M, S1, S1_predicted)

                # split is being done within append
                # expert.split()  # won't actually split if the condition is not met



                # random action or the best action
                term_print_str += ''.join(map(str, ("Exploring Rate: ", self.exploring_rate, '\n')))
                #print("Exploring Rate: ", self.exploring_rate)
                is_exploring = (random.random() < self.exploring_rate)

                #START ---- the Oudeyer way ----- START

                # # generate a list of possible action given the state
                # M_candidates = self.robot.get_possible_action(state=S1, num_sample=5)
                #
                # if is_exploring:
                #     M1 = random.choice(M_candidates)
                #
                # else:
                #     M1 = 0
                #     highest_L = float("-inf")
                #     for M_candidate in M_candidates:
                #         L = self.expert.evaluate_action(S1, M_candidate)
                #         if L > highest_L:
                #             M1 = M_candidate
                #             highest_L = L
                #     term_print_str += ''.join(map(str, ("Expected Reward: ", highest_L, '\n')))
                #     #print("Expected Reward", highest_L)
                #     L = highest_L
                # term_print_str += ''.join(map(str, ("Next Action: ", M1, '\n')))
                # #print("Next Action", M1)

                #END ---- the Oudeyer way ----- END

                #START ---- the Probabilistic way ----- START

                # generate a list of possible action given the state
                M_candidates = self.robot.get_possible_action(state=S1, num_sample=150)


                L_list = []
                for M_candidate in M_candidates:
                    L_list.append(self.expert.evaluate_action(S1, M_candidate))

                M_idx = weighted_choice_sub(L_list, min_percent=self.exploring_rate)
                L = max(L_list)
                term_print_str += ''.join(map(str, ("Highest Expected Reward: ", L, '\n')))
                #print("Highest Expected Reward", L)
                M1 = M_candidates[M_idx]
                term_print_str += ''.join(map(str, ("Next Action: ", M1, '\n')))
                #print("Next Action", M1)

                #END ---- the Probabilistic way ----- END

                print(term_print_str)

                # update learning rate based on reward
                if is_exploring and self.adapt_exploring_rate:  # if it was exploring, stick with the original learning rate
                    exploring_rate_range = [0.5, 0.01]
                    reward_range = [0.01, 100.0]
                    if L < reward_range[0]:
                        self.exploring_rate = exploring_rate_range[0]
                    elif L > reward_range[1]:
                        self.exploring_rate = exploring_rate_range[1]
                    else:
                        m = (exploring_rate_range[0] - exploring_rate_range[1])/(reward_range[0] - reward_range[1])
                        b = exploring_rate_range[0] - m*reward_range[0]
                        exploring_rate = m*L + b

                # record the mean errors of each region
                mean_errors = []
                region_ids = []
                self.expert.save_mean_errors(mean_errors)
                self.mean_error_history.append(copy(mean_errors))

                # set to current state

                S = S1
                if t < len(Mi):
                    M = Mi[t]
                else:
                    M = M1

                if t % 1000 == 0 or t >= self.sim_duration:
                    with open('expert_backup.pkl', 'wb') as output:
                        pickle.dump(self.expert, output, pickle.HIGHEST_PROTOCOL)

                    with open('action_history_backup.pkl', 'wb') as output:
                        pickle.dump(self.action_history, output, pickle.HIGHEST_PROTOCOL)

                    with open('state_history_backup.pkl', 'wb') as output:
                        pickle.dump(self.state_history, output, pickle.HIGHEST_PROTOCOL)

                    with open('mean_error_history_backup.pkl', 'wb') as output:
                        pickle.dump(self.mean_error_history, output, pickle.HIGHEST_PROTOCOL)

            self.visualize()


        def visualize(self):

            self.expert.print()

            # find out what are the ids that existed
            region_ids = sorted(list(zip(*self.mean_error_history[-1]))[0])

            Viz.plot_expert_tree(self.expert, region_ids)
            Viz.plot_evolution(self.state_history, title='State vs Time', y_label='S(t)', fig_num=1, subplot_num=261)
            # Viz.plot_evolution(self.action_history, title='Action vs Time', y_label='M(t)[1]', y_dim=1, fig_num=1, subplot_num=261)
            Viz.plot_evolution(self.action_history, title='Action vs Time', y_label='M(t)[0]', y_dim=0, fig_num=1, subplot_num=262)
            Viz.plot_model(self.expert, region_ids, x_idx=1, y_idx=0, fig_num=1, subplot_num=263)
            Viz.plot_model(self.expert, region_ids, x_idx=0, y_idx=0, fig_num=1, subplot_num=269)
            Viz.plot_regional_mean_errors(self.mean_error_history, region_ids, fig_num=1, subplot_num=234)
            Viz.plot_model_3D(self.expert, region_ids, x_idx=(0, 1), y_idx=0, fig_num=1, subplot_num=122)
            # Viz.plot_model_3D(self.expert, region_ids, x_idx=(1, 2), y_idx=0, fig_num=1, subplot_num=122, data_only=False)


            plt.ioff()
            plt.show()

    def run(self):


        teensy_names = self.teensy_manager.get_teensy_name_list()

        # initially update the Teensys with all the output parameters here
        self.update_output_params(teensy_names)

        # instantiation --- one CBLA engine per node
        self.write_barrier = threading.Barrier(len(teensy_names), action=self.send_commands, timeout=1000)
        self.read_barrier = threading.Barrier(len(teensy_names), action=self.read_barrier_action, timeout=1000)

        self.lock = threading.Lock()
        self.cbla_engine = dict()
        for teensy_name in teensy_names:
            # instantiate robots
            robot = self.Node(self, teensy_name)

            # instantiate CBLA Engines
            self.cbla_engine[teensy_name] = self.CBLA_Engine(robot)


    def read_barrier_action(self):
        self.update_input_states(self.teensy_manager.get_teensy_name_list())


# if __name__ == "__main__":
#
#     # number of time step
#     sim_duration = 500
#
#     # use saved expert
#     is_using_saved_expert = 0
#
#     # use adaptive learning rate
#     adapt_exploring_rate = False
#
#     # exploring rate
#     exploring_rate = 0.05
#
#
#     # instantiate a Robot
#     #robot = Robot(filename='SimpleData.pkl')
#     robot = Robot(low_bound=(-80,-80), high_bound=(80,80))
#     #robot = Robot(low_bound=(-80,), high_bound=(80,))
#
#
#     # instantiate an Expert
#     if is_using_saved_expert:
#         with open('expert_backup.pkl', 'rb') as input:
#             expert = pickle.load(input)
#         with open('action_history_backup.pkl', 'rb') as input:
#             action_history = pickle.load(input)
#         with open('state_history_backup.pkl', 'rb') as input:
#             state_history = pickle.load(input)
#         with open('mean_error_history_backup.pkl', 'rb') as input:
#             mean_error_history = pickle.load(input)
#
#         Mi = robot.get_possible_action(num_sample=1)
#
#     else:
#         expert = Expert()
#         action_history = []
#         state_history = []
#         mean_error_history = []
#
#         # initial training action
#         Mi = robot.get_possible_action(num_sample=100)
#
#     # initial conditions
#     t = 0
#     S = (0,)
#     M = Mi[0]
#     L = float("-inf")
#
#
#     while t < sim_duration:
#         t += 1
#
#         print("\nTest case t =", t, " -- ", S, M)
#
#         # have the expert make prediction
#         S1_predicted = expert.predict(S, M)
#         print("Predicted S1: ", S1_predicted)
#
#
#         # do action
#         action_history.append(M)
#         state_history.append(S)
#         robot.actuate(M)
#
#         # read sensor
#         S1 = robot.report()
#
#         # add exemplar to expert
#         expert.append(S + M, S1, S1_predicted)
#
#         # split is being done within append
#         # expert.split()  # won't actually split if the condition is not met
#
#
#
#         # random action or the best action
#         print("Exploring Rate: ", exploring_rate)
#         is_exploring = (random.random() < exploring_rate)
#
#         #START ---- the Oudeyer way ----- START
#
#         # # generate a list of possible action given the state
#         # M_candidates = robot.get_possible_action(state=S1, num_sample=50)
#         #
#         # if is_exploring:
#         #     M1 = random.choice(M_candidates)
#         #
#         # else:
#         #     M1 = 0
#         #     highest_L = float("-inf")
#         #     for M_candidate in M_candidates:
#         #         L = expert.evaluate_action(S1, M_candidate)
#         #         if L > highest_L:
#         #             M1 = M_candidate
#         #             highest_L = L
#         #
#         #     print("Expected Reward", highest_L)
#         #     L = highest_L
#         #
#         # print("Next Action", M1)
#
#         #END ---- the Oudeyer way ----- END
#
#         #START ---- the Probabilistic way ----- START
#
#         # generate a list of possible action given the state
#         M_candidates = robot.get_possible_action(state=S1, num_sample=50)
#
#
#         L_list = []
#         for M_candidate in M_candidates:
#             L_list.append(expert.evaluate_action(S1, M_candidate))
#
#         M_idx = weighted_choice_sub(L_list, min_percent=exploring_rate)
#         L = max(L_list)
#         print("Highest Expected Reward", L)
#         M1 = M_candidates[M_idx]
#         print("Next Action", M1)
#
#         #END ---- the Probabilistic way ----- END
#
#
#         # update learning rate based on reward
#         if is_exploring and adapt_exploring_rate:  # if it was exploring, stick with the original learning rate
#             exploring_rate_range = [0.5, 0.01]
#             reward_range = [0.01, 100.0]
#             if L < reward_range[0]:
#                 exploring_rate = exploring_rate_range[0]
#             elif L > reward_range[1]:
#                 exploring_rate = exploring_rate_range[1]
#             else:
#                 m = (exploring_rate_range[0] - exploring_rate_range[1])/(reward_range[0] - reward_range[1])
#                 b = exploring_rate_range[0] - m*reward_range[0]
#                 exploring_rate = m*L + b
#
#         # record the mean errors of each region
#         mean_errors = []
#         region_ids = []
#         expert.save_mean_errors(mean_errors)
#         mean_error_history.append(copy(mean_errors))
#
#         # set to current state
#
#         S = S1
#         if t < len(Mi):
#             M = Mi[t]
#         else:
#             M = M1
#
#
#         if t % 1000 == 0 or t >= sim_duration:
#             with open('expert_backup.pkl', 'wb') as output:
#                 pickle.dump(expert, output, pickle.HIGHEST_PROTOCOL)
#
#             with open('action_history_backup.pkl', 'wb') as output:
#                 pickle.dump(action_history, output, pickle.HIGHEST_PROTOCOL)
#
#             with open('state_history_backup.pkl', 'wb') as output:
#                 pickle.dump(state_history, output, pickle.HIGHEST_PROTOCOL)
#
#             with open('mean_error_history_backup.pkl', 'wb') as output:
#                 pickle.dump(mean_error_history, output, pickle.HIGHEST_PROTOCOL)
#
#
#     expert.print()
#
#     # find out what are the ids that existed
#     region_ids = sorted(list(zip(*mean_error_history[-1]))[0])
#
#     Viz.plot_expert_tree(expert, region_ids)
#     #Viz.plot_evolution(state_history, title='State vs Time', y_label='S(t)', fig_num=1, subplot_num=261)
#     Viz.plot_evolution(action_history, title='Action vs Time', y_label='M(t)[1]', y_dim=1, fig_num=1, subplot_num=261)
#     Viz.plot_evolution(action_history, title='Action vs Time', y_label='M(t)[0]', y_dim=0, fig_num=1, subplot_num=262)
#     Viz.plot_model(expert, region_ids, x_idx=1, y_idx=0, fig_num=1, subplot_num=263)
#     Viz.plot_model(expert, region_ids, x_idx=2, y_idx=0, fig_num=1, subplot_num=269)
#     Viz.plot_regional_mean_errors(mean_error_history, region_ids, fig_num=1, subplot_num=234)
#     #Viz.plot_model_3D(expert, region_ids, x_idx=(0, 1), y_idx=0, fig_num=1, subplot_num=122)
#     Viz.plot_model_3D(expert, region_ids, x_idx=(1, 2), y_idx=0, fig_num=1, subplot_num=122, data_only=False)
#
#
#     plt.ioff()
#     plt.show()
#

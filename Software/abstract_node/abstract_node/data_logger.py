__author__ = 'Matthew'

import threading
from queue import Queue
from collections import defaultdict
from copy import copy
from copy import deepcopy
import pickle
import os
import shutil
import datetime
import glob
from datetime import datetime, timedelta
from time import perf_counter, sleep, process_time
import shelve


class DataLogger(threading.Thread):

    datetime_str_fmt = "%Y-%m-%d_%H-%M-%S"
    datetime_str_fmt_us = "%Y-%m-%d_%H-%M-%S-%f"

    # packet keys
    packet_time_key = "packet_time"
    packet_type_key = "packet_type"
    packet_default_type = "data"

    # index keys
    idx_time_created_key = "time_created"
    idx_num_session_key = "num_session"

    # session key
    session_id_key = "session_id"
    session_datetime0_key = "session_datetime0"
    session_clock0_key = "session_clock0"


    def __init__(self, log_dir='log_data', log_header='generic_data',
                 log_timestamp=None, log_path=None,
                 **kwarg):

        now = datetime.now().strftime(DataLogger.datetime_str_fmt)

        # if a specific path is specified
        if isinstance(log_path, str) and os.path.isdir(log_path):
            log_dir_path = log_path
            log_name = os.path.split(log_dir_path)[-1]
        else:
            if log_timestamp == None:
                log_timestamp = now

            log_name =  '%s_%s' % (log_header, log_timestamp)
            log_dir_path = os.path.join(os.getcwd(), log_dir, log_name)

        # check if log directory even exist
        if not os.path.exists(log_dir_path):
            # create directory if does not exist
            os.makedirs(log_dir_path)

        # check if the log file exist
        log_path = os.path.join(log_dir_path, log_name)
        self.log_index_file = shelve.open(log_path, protocol=3, writeback=False)

        # if from previous session
        if self.log_index_file:

            try:
                self.log_index_file[DataLogger.idx_num_session_key] += 1
            except KeyError:
                raise KeyError('log file is corrupted!')

            curr_session = self.log_index_file[DataLogger.idx_num_session_key]
        else:
            curr_session = 1
            self.log_index_file[DataLogger.idx_time_created_key] = now
            self.log_index_file[DataLogger.idx_num_session_key] = curr_session

        self.log_index_file[str(curr_session)] = 'session_%03d' % curr_session

        # create the session's directory
        session_dir_path = os.path.join(log_dir_path, self.log_index_file[str(curr_session)])
        os.mkdir(session_dir_path)

        # open the shelve for the session
        session_path = os.path.join(session_dir_path, self.log_index_file[str(curr_session)])
        self.session_shelf = shelve.open(session_path, protocol=3, writeback=False)
        self.session_shelf[DataLogger.session_id_key] = curr_session

        # register the start time of the session
        self.clock0 = perf_counter()
        self.datetime0 = datetime.now()
        self.session_shelf[DataLogger.session_datetime0_key] = self.datetime0
        self.session_shelf[DataLogger.session_clock0_key] = self.clock0

        # queue for packet to come in
        self.__packet_queue = Queue()

        # data buffer in memory
        self.__data_buffer = defaultdict(list)

        # variables
        self.__program_terminating = False

        # parameters
        if 'sleep_time' in kwarg and isinstance(kwarg['sleep_time'], (float, int)):
            self.sleep_time = float(max(0.0, kwarg['sleep_time']))
        else:
            self.sleep_time = 0.0001

        if 'save_freq' in kwarg and isinstance(kwarg['save_freq'], (float, int)):
            self.save_freq = float(max(0.0, kwarg['save_freq']))
        else:
            self.save_freq = 2.0

        super(DataLogger, self).__init__(name='DataLogger', daemon=False)

    def run(self):

        last_saved_time = perf_counter()
        while not self.__program_terminating or not self.__packet_queue.empty():

            # saving run-time data to memory
            if not self.__packet_queue.empty():
                # get packet from queue
                node_name, packet_data = self.__packet_queue.get_nowait()

                # check if the packet has timestamp
                try:
                    packet_time = packet_data[DataLogger.packet_time_key]
                    if not isinstance(packet_time, float):
                        raise TypeError()
                except (KeyError, TypeError):
                    packet_time = perf_counter()
                    packet_data[DataLogger.packet_time_key] = packet_time

                # check if the packet has type
                try:
                    packet_type = packet_data[DataLogger.packet_type_key]
                    if not isinstance(packet_type, str):
                        raise TypeError()
                except (KeyError, TypeError):
                    packet_type = DataLogger.packet_default_type
                    packet_data[DataLogger.packet_type_key] = packet_type

                # save the packet data in the buffer
                self.__data_buffer[DataLogger.encode_struct(node_name, packet_type)].append(packet_data)

            # save data blocks to disk periodically
            if perf_counter() - last_saved_time > self.save_freq and not self.__program_terminating:
                self.__save_to_shelf()
                last_saved_time = perf_counter()

            # don't sleep if program is terminating
            if not self.__program_terminating:
                sleep(self.sleep_time)

        # save all remaining data in buffer to disk
        self.__save_to_shelf()
        print("Data Logger saved all data to disk.")

    def append_data_packet(self, node_name, data_packet):
        self.__packet_queue.put((node_name, copy(data_packet)))

    def end_data_collection(self):
        self.__program_terminating = True

    def __save_to_shelf(self):
        for data_block_key, data_block in self.__data_buffer.items():

            if data_block and len(data_block) > 0:
                # use the fist packet's time as timestamp for the block
                block_timestamp = data_block[0][DataLogger.packet_time_key]
                # convert CPU time to datetime then to a string
                block_time_str = self.__clock2datetime(block_timestamp).strftime(DataLogger.datetime_str_fmt_us)
                # save to the shelf
                self.session_shelf[DataLogger.encode_struct(data_block_key, block_time_str)] = data_block

        # clear data_buffer
        self.__data_buffer = defaultdict(list)

    def __clock2datetime(self, clock_t: float):
        return self.datetime0 + timedelta(0, clock_t - self.clock0)

    @classmethod
    # return an dictionary from the files for plotting purposes
    def retrieve_data(cls, log_dir: str, log_header=None, log_timestamp=None, log_name=None):

        # check if the log's directory exists
        if isinstance(log_dir, str) and os.path.isdir(log_dir):
            log_dir_path = log_dir
        elif isinstance(log_dir, str) and os.path.isdir(os.path.join(os.getcwd(), log_dir)):
            log_dir_path = os.path.join(os.getcwd(), log_dir)
        else:
            raise FileNotFoundError('%s cannot be found!' % str(log_dir))

        # if a specific log file is specified
        if isinstance(log_name, str) and os.path.isdir(os.path.join(log_dir_path, log_name)):
            log_path = os.path.join(log_dir_path, log_name)

        # if the log header and the timestamp is specified
        elif isinstance(log_header, str) and isinstance(log_timestamp, str):
            log_path = os.path.join(log_dir_path, '%s_%s' % (log_header, log_timestamp))

        # if timestamp is not specified
        else:
            # use the latest data log
            all_log_dir = []
            for dir in os.listdir(log_dir_path):
                dir_path = os.path.join(log_dir_path, dir)
                if os.path.isdir(dir_path):

                    # if log_header is specified
                    if isinstance(log_header, str):
                        if log_header in dir:
                            # append only the ones matches the log headers
                            all_log_dir.append(dir_path)
                    else:
                        all_log_dir.append(dir_path)

            if len(all_log_dir) > 0:
                log_path = max(all_log_dir, key=os.path.getmtime)
            else:
                raise FileNotFoundError('Cannot find any relevant log files in %s' % log_dir_path)

        # open the log's index
        log_index_name = os.path.split(log_path)[-1]
        log_index_path = os.path.join(log_path, log_index_name)
        log_index_file = shelve.open(log_index_path, flag='r', protocol=3, writeback=False)

        # create an array of dictionary for each session
        num_session = int(log_index_file[DataLogger.idx_num_session_key])
        log_sessions = []
        for session_id in range(1, num_session+1):
            session_shelf_key = log_index_file[str(session_id)]
            session_shelf_path = os.path.join(log_path, session_shelf_key, session_shelf_key)
            session_shelf = shelve.open(session_shelf_path, flag='r', protocol=3, writeback=False)

            data_dict = dict()
            for data_key, packet_blocks in session_shelf.items():
                data_struct = DataLogger.decode_struct(data_key)
                DataLogger.__insert_to_struct(data_dict, data_struct, packet_blocks)

            log_sessions.append(data_dict)

        return log_sessions

    @staticmethod
    def __insert_to_struct(data_dict, structure, value):

        # type checking
        if not isinstance(structure, (tuple, list)) and len(structure) < 1:
            raise TypeError('sturcture must be a tuple!')

        # instantiate dict
        if not isinstance(data_dict, dict):
            raise TypeError('data_dict must be a dictionary!')

        top_level = structure[0]

        # base case
        if len(structure) == 1:
            if top_level in data_dict:
                raise ValueError("%s is already filled" % top_level)
            data_dict[top_level] = value
        else:
            # instantiate dict
            if not top_level in data_dict:
                data_dict[top_level] = dict()

            DataLogger.__insert_to_struct(data_dict[top_level], structure[1:], value)

    @classmethod
    def encode_struct(cls, *struct_labels, separator='//'):

        return separator.join(struct_labels)

    @classmethod
    def decode_struct(cls, struct_str: str, separator='//'):

        if not isinstance(struct_str, str):
            raise ValueError("struct_str must be a str!")
        return struct_str.split(separator)


class DataPlotter():

    def __init__(self, log_dir, log_header=None, log_timestamp=None, log_name=None):

        self.log_dict = DataLogger.retrieve_data(log_dir=log_dir, log_header=log_header,
                                                log_timestamp=log_timestamp, log_name=log_name)


# test script
if __name__ == '__main__':

    create_new_log = True
    log_dir_path = os.path.join(os.getcwd(), 'data_log')

    if create_new_log:
        latest_log_dir = None
    else:
        # use the latest data log
        all_log_dir = []
        for dir in os.listdir(log_dir_path):
            dir_path = os.path.join(log_dir_path, dir)
            if os.path.isdir(dir_path):
                all_log_dir.append(dir_path)
        latest_log_dir = max(all_log_dir, key=os.path.getmtime)

    data_logger = DataLogger(log_dir=log_dir_path, log_path=latest_log_dir)
    data_logger.start()

    pack_dict = dict()
    for i in range(10000):

        curr_time = perf_counter()
        pack_dict[DataLogger.packet_type_key] = i
        pack_dict[DataLogger.packet_time_key] = curr_time

        # data_logger.append_data_packet('test_node', {DataLogger.packet_time_key:curr_time})
        data_logger.append_data_packet('test_node', pack_dict)
